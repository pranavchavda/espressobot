import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import OpenAI from 'openai';

const prisma = new PrismaClient();
const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const router = Router();

// Server-Sent Events streaming endpoint for chat responses
router.post('/', async (req, res) => {
  try {
    const { message, conv_id, image } = req.body || {};
    if (typeof message !== 'string' || !message.trim()) {
      return res.status(400).json({ error: 'Request body must include a non-empty message string' });
    }

    const USER_ID = 1;
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

    // Persist user message
    await prisma.messages.create({
      data: {
        conv_id: conversation.id,
        role: 'user',
        content: message,
      },
    });

    // Fetch full history for context
    const history = await prisma.messages.findMany({
      where: { conv_id: conversation.id },
      orderBy: { id: 'asc' },
    });
    const inputMessages = history.map((m) => ({
      type: 'message',
      role: m.role === 'assistant' ? 'assistant' : 'user',
      content: m.content,
    }));
    if (image) {
      const imageUrl = image.type === 'data_url' ? image.data : image.url;
      inputMessages.push({
        type: 'message',
        role: 'user',
        content: [
          {
            type: 'input_image',
            detail: process.env.VISION_DETAIL || 'auto',
            image_url: imageUrl,
          },
        ],
      });
    }
    console.log(inputMessages);
    // Initialize SSE headers
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

    // Notify client of conversation ID (for new conv)
    res.write(`data: ${JSON.stringify({ conv_id: conversation.id })}\n\n`);

    // Stream responses from OpenAI Responses API
    const responseModel = image ? process.env.VISION_MODEL : process.env.OPENAI_MODEL;
    const stream = await openai.responses.create({
      model: responseModel,
      input: inputMessages,
      text: { format: { type: 'text' } },
      tools: [
        {
          type: 'web_search_preview',
          user_location: { type: 'approximate' },
          search_context_size: 'medium',
        },
        {
          type: 'mcp',
          server_label: 'iDrinkCoffee_Shopify_Tools',
          server_url: 'https://webhook-listener-pranavchavda.replit.app/mcp',
          allowed_tools: [
            'upload_to_sku_vault',
            "run_full_shopify_graphql_mutation",
            "run_full_shopify_graphql_query",    
            'update_pricing',
            'product_create_full',
            'add_product_to_collection',
            'set_metafield',
            'variant_create',
            'product_create',
            'get_single_product',
            'search_products',
            'create_feature_box',
            'product_update',
            'product_tags_add',
            'product_tags_remove'
          ],
          require_approval: 'never',
        },
      ],
      stream: true,
    });

    let assistantResponse = '';
    for await (const event of stream) {
      if (event.delta) {
        assistantResponse += event.delta;
      } else if (event.content) {
        assistantResponse += event.content;
      }
      res.write(`data: ${JSON.stringify(event)}\n\n`);
    }

    // Persist assistant message
    await prisma.messages.create({
      data: {
        conv_id: conversation.id,
        role: 'assistant',
        content: assistantResponse,
      },
    });
    history.push({ role: 'assistant', content: assistantResponse });

    // Generate a concise title for this conversation using the Title Creator agent
    try {
      const titlePrompt = [
        {
          role: 'system',
          content:
            'You are a conversation title generator. Given the messages in a chat conversation, provide a concise title (max 60 characters) summarizing the content. Respond with the title only.',
        },
        ...history.map((m) => ({ role: m.role || 'assistant', content: m.content })),
      ];
      const titleCompletion = await openai.chat.completions.create({
        model: process.env.OPENAI_MODEL,
        messages: titlePrompt,
      });
      const newTitle = titleCompletion.choices?.[0]?.message?.content?.trim();
      if (newTitle) {
        await prisma.conversations.update({
          where: { id: conversation.id },
          data: { title: newTitle },
        });
        // Notify client of updated title
        res.write(`data: ${JSON.stringify({ new_title: newTitle })}\n\n`);
      }
    } catch (titleErr) {
      console.error('Title generation error:', titleErr);
    }

    // Signal completion
    res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
    res.end();
  } catch (err) {
    console.error('Stream Chat error:', err);
    res.write(`data: ${JSON.stringify({ error: err.message || 'Internal server error' })}\n\n`);
    res.end();
  }
});

export default router;