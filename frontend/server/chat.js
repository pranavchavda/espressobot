import { Router } from 'express';

import { PrismaClient } from '@prisma/client';
import OpenAI from 'openai';

const prisma = new PrismaClient();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const router = Router();

router.get('/', (req, res) => {
  res.json({ message: 'Chat API is working' });
});

router.post('/', async (req, res) => {
  try {
    const { messages, conv_id } = req.body || {};
    if (!Array.isArray(messages)) {
      return res.status(400).json({ error: 'Request body must include a messages array' });
    }

    const USER_ID = 1;
    // Ensure a default local user exists to satisfy foreign key constraints
    await prisma.users.upsert({
      where: { id: USER_ID },
      update: {},
      create: {
        id: USER_ID,
        email: 'local@local.dev',
        password_hash: '',
        is_whitelisted: true,
        created_at: new Date(),
      },
    });
    let conversation;
    if (conv_id) {
      conversation = await prisma.conversations.findUnique({ where: { id: conv_id } });
      if (!conversation) {
        return res.status(404).json({ error: 'Conversation not found' });
      }
    } else {
      conversation = await prisma.conversations.create({
        data: {
          user_id: USER_ID,
          title: `Conversation ${new Date().toISOString()}`,
          filename: `conversation-${Date.now()}.json`,
        },
      });
    }

    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      await prisma.messages.create({
        data: {
          conv_id: conversation.id,
          role: lastMessage.role,
          content: lastMessage.content,
        },
      });
    }

    // Format prior messages as input blocks for the Responses API
    const inputMessages = messages.map((m) => ({
      type: 'message',
      role: m.role,
      content: m.content,
    }));
    const response = await openai.responses.create({
      model: process.env.OPENAI_MODEL,
      input: inputMessages,
      text: { format: { type: 'text' } },
      tools: [
        {
          type: 'web_search_preview',
          user_location: { type: 'approximate' },
          search_context_size: 'medium',
        },
        {
          type: "mcp",
          server_label: "iDrinkCoffee_Shopify_Tools",
          server_url: "https://webhook-listener-pranavchavda.replit.app/mcp",
          allowed_tools: [
            "upload_to_sku_valut",
            "update_pricing",
            "product_create_full",
            "add_product_to_collection",
            "get_collections",
            "set_metafield",
            "variant_create",
            "product_create",
            "get_single_product",
            "search_products",
            "create_feature_box",
            "get_product",
            "product_update",
            "product_tags_add",
            "product_tags_remove"
          ],
          require_approval: "never"
        }
      ],
    });

    // Extract assistant message text from Responses API output
    const output = response.output ?? [];
    const firstMessage = output.find((o) => o.type === 'message');
    let replyContent = '';
    if (firstMessage && Array.isArray(firstMessage.content)) {
      replyContent = firstMessage.content
        .filter((c) => c.type === 'output_text' && typeof c.text === 'string')
        .map((c) => c.text)
        .join('');
    }
    const assistantRole = firstMessage?.role || 'assistant';

    await prisma.messages.create({
      data: {
        conv_id: conversation.id,
        role: assistantRole,
        content: replyContent,
      },
    });

    return res.json({ reply: replyContent, conv_id: conversation.id });
  } catch (err) {
    console.error('Chat API error:', err);
    res.status(500).json({ error: err.message || 'Internal server error' });
  }
});

export default router;