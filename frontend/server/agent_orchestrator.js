import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import {
  Runner,
  RunConfig
} from 'openai-agents-js';
import { synthesizerAgent } from './agents.js';

const prisma = new PrismaClient();
const router = Router();

// Helper to send SSE messages
function sendSse(res, eventName, data) {
  if (res.writableEnded) {
    console.warn(`BACKEND Orchestrator: Attempted to send SSE event '${eventName}' after stream ended.`);
    return;
  }
  try {
    res.write(`data: ${JSON.stringify({ type: eventName, data })}\n\n`);
  } catch (e) {
    console.error(`BACKEND Orchestrator: Error writing to SSE stream (event: ${eventName}):`, e.message);
    // Consider ending the stream if a write error occurs, as it's likely unrecoverable.
    if (!res.writableEnded) {
      res.end();
    }
  }
}

router.post('/run', async (req, res) => {
  const { message, conv_id: existing_conv_id } = req.body || {};
  let conversationId = existing_conv_id;

  // Setup SSE
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();

  try {
    if (typeof message !== 'string' || !message.trim()) {
      sendSse(res, 'error', { message: 'Request body must include a non-empty message string' });
      return res.end();
    }

    const USER_ID = 1; // Assuming a fixed user ID for now
    let conversation;

    if (conversationId) {
      conversation = await prisma.conversations.findUnique({ where: { id: conversationId } });
      if (!conversation) {
        sendSse(res, 'error', { message: 'Conversation not found' });
        return res.end();
      }
    } else {
      conversation = await prisma.conversations.create({
        data: {
          user_id: USER_ID,
          title: `AgentV2 ${new Date().toISOString()}`,
          filename: `agentv2-${Date.now()}.json`,
        },
      });
      conversationId = conversation.id;
    }
    sendSse(res, 'conversation_id', { conv_id: conversationId });

    await prisma.messages.create({
      data: { conv_id: conversationId, role: 'user', content: message },
    });

    const { image } = req.body;
    let currentUserMessageContent;
    if (image && (image.url || image.data)) {
      const imageUrl = image.type === 'data_url' ? image.data : image.url;
      const textPart = { type: 'input_text', text: message || '' };
      const imagePart = { type: 'input_image', image_url: imageUrl, detail: process.env.VISION_DETAIL || 'auto' };
      currentUserMessageContent = [textPart, imagePart];
    } else {
      currentUserMessageContent = message;
    }

    const history = await prisma.messages.findMany({
      where: { conv_id: conversationId },
      orderBy: { id: 'asc' },
    });
    const MAX_HISTORY_MESSAGES = parseInt(process.env.MAX_HISTORY_MESSAGES || '10', 10);
    const recentHistory = history.slice(-MAX_HISTORY_MESSAGES);
    const historyText = recentHistory.map(m => {
      if (m.role === 'assistant' && m.content.length > 500) {
        return `${m.role}: ${m.content.substring(0, 497)}...`;
      }
      return `${m.role}: ${m.content}`;
    }).join('\n');

    const runConfig = new RunConfig({
      maxTurns: 5,
      workflowName: 'AgenticChatOrchestration'
    });

    // Run the SynthesizerAgent end-to-end (with planner & dispatcher handoffs)
    // Notify UI that synthesizer (agent) is starting
    sendSse(res, 'synthesizer_status', { status: 'started' });
    const orchestratorInput = { originalQuery: currentUserMessageContent, conversationHistory: historyText };
    const orchestratorStream = await Runner.runStreamed(
      synthesizerAgent,
      JSON.stringify(orchestratorInput),
      { runConfig }
    );
    let fullAssistantResponse = '';
    for await (const event of orchestratorStream.streamEvents()) {
      // Handle planner, dispatcher, and task executor tool calls uniformly
      if (event.type === 'tool_call_started' || event.type === 'tool_call_completed' || event.type === 'tool_call_failed') {
        const {
          toolCallId = `unknown_${Date.now()}`,
          toolName = 'Unknown Tool',
          toolInput,
          output,
          error
        } = event;
        const status =
          event.type === 'tool_call_started' ? 'started' : event.type === 'tool_call_completed' ? 'completed' : 'error';

        // Plan handoff
        if (toolName === 'plan') {
          const payload = { status };
          if (status === 'completed') payload.plan = output;
          if (status === 'completed' || status === 'error') payload.conversationId = conversationId;
          sendSse(res, 'planner_status', payload);

        // Dispatch handoff
        } else if (toolName === 'dispatch') {
          const payload = { status };
          sendSse(res, 'dispatcher_status', payload);

        // Individual task executor events
        } else {
          const payload = {
            tool_call_id: toolCallId,
            tool_name: toolName,
            tool_input: toolInput,
            status
          };
          if (status === 'completed') payload.output = output;
          if (status === 'error') payload.error = error?.message || error;
          sendSse(res, 'dispatcher_event', payload);
        }

      // Streamed assistant text tokens
      } else if (event.type === 'agent_text_delta_stream_event' && typeof event.delta === 'string') {
        sendSse(res, 'assistant_delta', { delta: event.delta });
        fullAssistantResponse += event.delta;
      }
    }
    if (fullAssistantResponse.trim()) {
      await prisma.messages.create({
        data: { conv_id: conversationId, role: 'assistant', content: fullAssistantResponse },
      });
    }
    // Notify UI that synthesizer (agent) has completed
    sendSse(res, 'synthesizer_status', { status: 'completed' });

  } catch (error) {
    console.error('BACKEND Orchestrator: Orchestrator error:', error.message, error.stack);
    if (!res.headersSent && !res.writableEnded) {
        // Only set headers if not already sent and stream is writable
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache, no-transform');
        res.setHeader('Connection', 'keep-alive');
        // Avoid res.flushHeaders() here as it can also error if stream state is bad
    }
    if (!res.writableEnded) { 
        sendSse(res, 'error', { message: 'An unexpected error occurred in the orchestrator.', details: error.message });
    } else {
        console.warn("BACKEND Orchestrator: Stream ended before error could be sent to client in catch block.");
    }
    // Ensure the stream is ended if an error occurs and we haven't explicitly ended it.
    if (!res.writableEnded) {
        console.log("BACKEND Orchestrator: Ending stream in main catch block due to unhandled error.");
        res.end();
    }
  } finally {
    sendSse(res, 'done', {});
    res.end();
  }
});

export default router;
