import { Router } from 'express';
import * as prismaClient from '@prisma/client';
import { run } from '@openai/agents';
import { basicChatAgent } from './basic-agent.js';

// Debug logging
console.log('======= BASIC_ORCHESTRATOR.JS INITIALIZATION =======');

const PrismaClient = prismaClient.PrismaClient;
const prisma = new PrismaClient();
const router = Router();

console.log('Created PrismaClient and router');

// Helper to send SSE messages
function sendSse(res, eventName, data) {
  if (res.writableEnded) {
    console.warn(`BACKEND Orchestrator: Attempted to send SSE event '${eventName}' after stream ended.`);
    return;
  }
  try {
    // Use standard SSE format with separate event and data lines
    // This matches what the frontend expects
    console.log(`Sending SSE event: ${eventName}`);
    res.write(`event: ${eventName}\n`);
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  } catch (e) {
    console.error(`BACKEND Orchestrator: Error writing to SSE stream (event: ${eventName}):`, e.message);
    if (!res.writableEnded) {
      res.end();
    }
  }
}

router.post('/run', async (req, res) => {
  console.log('\n========= BASIC ORCHESTRATOR REQUEST RECEIVED =========');
  const { message, conv_id: existing_conv_id } = req.body || {};
  let conversationId = existing_conv_id;

  // Setup SSE
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();
  
  console.log('SSE headers set');

  try {
    if (typeof message !== 'string' || !message.trim()) {
      sendSse(res, 'error', { message: 'Request body must include a non-empty message string' });
      return res.end();
    }
    
    console.log('Request message:', message);

    const USER_ID = 1; // Assuming a fixed user ID for now
    let conversation;

    if (conversationId) {
      conversation = await prisma.conversations.findUnique({ where: { id: conversationId } });
      if (!conversation) {
        sendSse(res, 'error', { message: 'Conversation not found' });
        return res.end();
      }
      console.log('Found existing conversation:', conversationId);
    } else {
      conversation = await prisma.conversations.create({
        data: {
          user_id: USER_ID,
          title: `Conversation ${new Date().toISOString()}`,
          filename: `conversation-${Date.now()}.json`,
        },
      });
      conversationId = conversation.id;
      console.log('Created new conversation:', conversationId);
    }

    // Persist user message
    await prisma.messages.create({
      data: {
        conv_id: conversationId,
        role: 'user',
        content: message,
      },
    });
    console.log('Persisted user message');

    // Fetch conversation history
    const history = await prisma.messages.findMany({
      where: { conv_id: conversationId },
      orderBy: { id: 'asc' },
    });

    // Format conversation history
    const MAX_HISTORY_MESSAGES = parseInt(process.env.MAX_HISTORY_MESSAGES || '10', 10);
    const recentHistory = history.slice(-MAX_HISTORY_MESSAGES);
    const historyText = recentHistory.map(m => `${m.role}: ${m.content}`).join('\n');
    
    console.log('Formatted conversation history with', recentHistory.length, 'messages');

    // Prepare agent input
    let agentInput = message;
    if (historyText) {
      agentInput = `Previous conversation:\n${historyText}\n\nUser: ${message}`;
    }
    
    console.log('Agent input prepared');
    
    // Notify client with conversation ID
    sendSse(res, 'conv_id', { conversationId });

    // Run agent
    let assistantResponse = '';
    try {
      // Run the agent directly using the run() function - following the examples pattern
      console.log('Running basic agent...');
      console.log('Agent input (first 100 chars):', agentInput.substring(0, 100) + (agentInput.length > 100 ? '...' : ''));
      
      // Use the run function directly from @openai/agents
      const result = await run(basicChatAgent, agentInput);
      console.log('Agent run completed');
      
      // Extract the final output from the result
      assistantResponse = result.finalOutput || '';
      console.log('Response received, length:', assistantResponse.length);
      
      // First, send the conversation ID (needed for UI to work properly)
      sendSse(res, 'conversation_id', { conv_id: conversationId });
      
      // Stream response to client as a single delta (could be chunked for real streaming)
      sendSse(res, 'assistant_delta', { delta: assistantResponse });
      
      // Send done event to mark completion
      sendSse(res, 'done', {});
      
    } catch (agentError) {
      console.error('Error running agent:', agentError);
      throw agentError;
    }
    
    // Persist assistant message
    if (assistantResponse.trim()) {
      await prisma.messages.create({
        data: {
          conv_id: conversationId,
          role: 'assistant',
          content: assistantResponse,
        },
      });
      console.log('Persisted assistant response');
    }

  } catch (error) {
    console.error('\n====== BASIC ORCHESTRATOR ERROR ======');
    console.error('Error:', error);
    console.error('Error name:', error.name);
    console.error('Error message:', error.message);
    console.error('Error stack:', error.stack);
    
    if (!res.writableEnded) {
      sendSse(res, 'error', { 
        message: 'An error occurred', 
        details: error.message
      });
    }
    
    if (!res.writableEnded) {
      console.log("BACKEND Orchestrator: Ending stream due to error.");
      res.end();
    }
  } finally {
    if (!res.writableEnded) {
      sendSse(res, 'done', {});
      res.end();
      console.log('Stream ended with done event');
    }
    
    console.log('========= BASIC ORCHESTRATOR REQUEST COMPLETED =========');
  }
});

export default router;
