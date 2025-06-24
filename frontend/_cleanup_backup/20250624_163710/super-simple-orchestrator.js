import { Router } from 'express';
import pkg from '@prisma/client';
import { run } from '@openai/agents';
import { superSimpleAgent } from './super-simple-agent.js';

// Debug logging
console.log('======= SUPER-SIMPLE-ORCHESTRATOR.JS INITIALIZATION =======');

const { PrismaClient } = pkg;
const prisma = new PrismaClient();
const router = Router();

console.log('Created PrismaClient and router');

// Helper to send SSE messages with guaranteed delivery
function sendSse(res, eventName, data) {
  if (res.writableEnded) {
    console.warn(`BACKEND Orchestrator: Attempted to send SSE event '${eventName}' after stream ended.`);
    return;
  }
  try {
    // Use standard SSE format with separate event and data lines
    console.log(`Sending SSE event: ${eventName} with data:`, JSON.stringify(data));
    
    // Write the event type
    res.write(`event: ${eventName}\n`);
    
    // Write the data payload
    res.write(`data: ${JSON.stringify(data)}\n\n`);
    
    // Explicit flush to ensure immediate delivery
    if (res.flush && typeof res.flush === 'function') {
      res.flush();
    }

    // Return true to indicate success
    return true;
  } catch (e) {
    console.error(`BACKEND Orchestrator: Error writing to SSE stream (event: ${eventName}):`, e.message);
    return false;
  }
}

router.post('/run', async (req, res) => {
  try {
    console.log('\n========= SUPER-SIMPLE ORCHESTRATOR REQUEST RECEIVED =========');
    
    // Enhanced SSE headers setup
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no' // Prevents Nginx proxy buffering
    });
    console.log('SSE headers set with explicit writeHead for better compatibility');
  
    const { message, conv_id: existing_conv_id } = req.body || {};
    let conversationId = existing_conv_id;

    // Validate input message
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

    // Set up error handler for client disconnection
    req.on('close', () => {
      console.log(`Client disconnected for conversation: ${conversationId}`);
      if (!res.writableEnded) {
        try {
          // Send one final done event before closing
          sendSse(res, 'done', { status: 'client_disconnected' });
          res.end();
        } catch (e) {
          console.error('Error during cleanup after client disconnect:', e);
        }
      }
    });

    // Run agent without any MCP server
    let assistantResponse = '';
    try {
      // Run the agent directly using the run() function - following the examples pattern
      console.log('Running super simple agent (NO MCP)...');
      console.log('Agent input (first 100 chars):', agentInput.substring(0, 100) + (agentInput.length > 100 ? '...' : ''));
      
      // Use the run function directly from @openai/agents
      const result = await run(superSimpleAgent, agentInput);
      console.log('Agent run completed');
      
      // Extract the final output from the result
      assistantResponse = result.finalOutput || '';
      console.log('Response received, length:', assistantResponse.length);
      
      // First, send the conversation ID with an explicit event name
      res.write('event: conversation_id\n');
      res.write(`data: ${JSON.stringify({ conv_id: conversationId })}\n\n`);
      res.flush && res.flush();
      
      // Stream response to client as a single delta with explicit event name
      res.write('event: assistant_delta\n');
      res.write(`data: ${JSON.stringify({ delta: assistantResponse })}\n\n`);
      res.flush && res.flush();
      
      // Send synthesizer status with explicit event name
      res.write('event: synthesizer_status\n');
      res.write(`data: ${JSON.stringify({ status: 'completed' })}\n\n`);
      res.flush && res.flush();
      
      // Send the done event with explicit event name - THIS IS CRITICAL
      res.write('event: done\n');
      res.write(`data: ${JSON.stringify({ status: 'complete' })}\n\n`);
      res.flush && res.flush();
      
      // Additional empty event to ensure flushing
      res.write(':\n\n');
      res.flush && res.flush();
      
      console.log('All SSE events sent, stream should be complete');
      
    } catch (agentError) {
      console.error('Error running agent:', agentError);
      assistantResponse = `Error: ${agentError.message}`;

      // Even in error condition, send proper SSE events with explicit format
      try {
        // Send error message as assistant_delta
        res.write('event: assistant_delta\n');
        res.write(`data: ${JSON.stringify({ delta: assistantResponse })}\n\n`);
        res.flush && res.flush();
        
        // Send error status
        res.write('event: error\n');
        res.write(`data: ${JSON.stringify({ message: agentError.message })}\n\n`);
        res.flush && res.flush();
        
        // CRITICAL: Always send done event even in error condition
        res.write('event: done\n');
        res.write(`data: ${JSON.stringify({ status: 'error' })}\n\n`);
        res.flush && res.flush();
        
        console.log('All error SSE events sent, stream should be complete');
      } catch (sseError) {
        console.error('Error sending SSE error events:', sseError);
      }
    }
    
    // Always ensure the response is ended properly
    if (!res.writableEnded) {
      try {
        res.end();
      } catch (endError) {
        console.error('Error ending response stream:', endError);
      }
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
    console.error('\n====== SUPER-SIMPLE ORCHESTRATOR ERROR ======');
    console.error('Error:', error);
    console.error('Error name:', error.name);
    console.error('Error message:', error.message);
    console.error('Error stack:', error.stack);
    
    if (!res.writableEnded) {
      // Send error event
      sendSse(res, 'error', { 
        message: 'An error occurred', 
        details: error.message
      });
      
      // Always send done event to ensure UI updates
      sendSse(res, 'done', { status: 'error' });
      
      console.log("BACKEND Orchestrator: Ending stream due to error.");
      res.end();
    }
  } finally {
    if (!res.writableEnded) {
      // Make sure the done event is sent in the finally block as well
      sendSse(res, 'done', { status: 'complete' });
      res.end();
      console.log('Stream ended with done event');
    }
    
    console.log('========= SUPER-SIMPLE ORCHESTRATOR REQUEST COMPLETED =========');
  }
});

export default router;
