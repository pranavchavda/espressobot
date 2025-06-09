import { Router } from 'express';
import * as prismaClient from '@prisma/client';
import OpenAI from 'openai';

// Debug logging for startup sequence
console.log('======= STREAM_CHAT.JS INITIALIZATION =======');
console.log('Loading @prisma/client module:', !!prismaClient);

const PrismaClient = prismaClient.PrismaClient;
console.log('PrismaClient loaded:', !!PrismaClient);

try {
  const testPrisma = new PrismaClient();
  console.log('PrismaClient instance created successfully');
} catch (err) {
  console.error('CRITICAL: Failed to create PrismaClient instance:', err);
}

const prisma = new PrismaClient();

// Detailed debug logging for OpenAI client initialization
console.log('Creating OpenAI client with API key:', process.env.OPENAI_API_KEY ? `${process.env.OPENAI_API_KEY.substring(0, 3)}...${process.env.OPENAI_API_KEY.slice(-4)}` : 'NOT SET');
let openai;
try {
  openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
  console.log('OpenAI client created successfully:', !!openai);
} catch (err) {
  console.error('CRITICAL: Failed to create OpenAI client:', err);
}
const router = Router();

console.log('Router created');

// Server-Sent Events streaming endpoint for chat responses
router.post('/', async (req, res) => {
  console.log('\n========= STREAM CHAT REQUEST RECEIVED =========');
  console.log('Request body:', JSON.stringify(req.body).substring(0, 200) + (JSON.stringify(req.body).length > 200 ? '...' : ''));
  console.log('Headers:', JSON.stringify(req.headers).substring(0, 200));
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
    console.log('Input messages:', JSON.stringify(inputMessages).substring(0, 200) + '...');
    
    // Initialize SSE headers
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders();

    // Notify client of conversation ID (for new conv)
    res.write(`data: ${JSON.stringify({ conv_id: conversation.id })}\n\n`);

    // Stream responses from OpenAI Responses API
    console.log('\n--- PREPARING OPENAI API REQUEST ---');
    const responseModel = image ? process.env.VISION_MODEL : process.env.OPENAI_MODEL;
    console.log('Using model:', responseModel);
    console.log('Input messages count:', inputMessages.length);
    if (inputMessages.length > 0) {
      console.log('First message preview:', JSON.stringify(inputMessages[0]).substring(0, 100) + '...');
    }
    
    console.log('Making OpenAI API request...');
    let stream;
    try {
      stream = await openai.responses.create({
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
            headers: {
              "Authorization": "Bearer ihwvXarctxYJH0OUgA8Hg/WJX+NSPuOka7uRKLNENDU="
            },
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
      console.log('OpenAI API request successful, received stream response');
    } catch (apiError) {
      console.error('Error making OpenAI API request:', apiError);
      if (apiError.response) {
        console.error('API response error:', {
          status: apiError.response.status,
          statusText: apiError.response.statusText,
          headers: apiError.response.headers,
          data: apiError.response.data
        });
      }
      throw apiError;
    }

    let assistantResponse = '';
    console.log('Starting to process stream events');
    let eventCount = 0;
    try {
      for await (const event of stream) {
        eventCount++;
        if (eventCount <= 3 || eventCount % 20 === 0) {
          console.log(`Stream event ${eventCount}:`, JSON.stringify(event).substring(0, 100) + '...');
        }
        if (event.delta) {
          assistantResponse += event.delta;
        } else if (event.content) {
          assistantResponse += event.content;
        }
        try {
          res.write(`data: ${JSON.stringify(event)}\n\n`);
        } catch (writeErr) {
          console.error('Error writing event to response stream:', writeErr);
        }
      }
      console.log(`Finished processing ${eventCount} stream events`);
    } catch (streamErr) {
      console.error('Error processing stream events:', streamErr);
      throw streamErr;
    }

    // Persist assistant message
    console.log('Persisting assistant message to database, length:', assistantResponse.length);
    try {
      await prisma.messages.create({
        data: {
          conv_id: conversation.id,
          role: 'assistant',
          content: assistantResponse,
        },
      });
      console.log('Successfully saved assistant message to database');
    } catch (dbErr) {
      console.error('Error saving assistant message to database:', dbErr);
    }
    history.push({ role: 'assistant', content: assistantResponse });

    // Generate a concise title for this conversation using the Title Creator agent
    console.log('Generating conversation title...');
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
    console.log('Signaling completion to client');
    try {
      res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
      res.end();
      console.log('Stream chat request completed successfully');
    } catch (endErr) {
      console.error('Error ending response:', endErr);
    }
  } catch (err) {
    console.error('\n====== STREAM CHAT ERROR ======');
    console.error('Error:', err);
    console.error('Error name:', err.name);
    console.error('Error message:', err.message);
    console.error('Error stack:', err.stack);
    if (err.cause) {
      console.error('Error cause:', err.cause);
    }
    if (err.response) {
      console.error('OpenAI API response error:', {
        status: err.response.status,
        statusText: err.response.statusText,
        headers: err.response.headers,
        data: err.response.data
      });
    }
    
    try {
      res.write(`data: ${JSON.stringify({ error: err.message || 'Internal server error' })}\n\n`);
      res.end();
    } catch (responseErr) {
      console.error('Error sending error response:', responseErr);
    }
  }
  console.log('========= REQUEST HANDLER EXITED =========');
});

export default router;
