import { Router } from 'express';
import { PrismaClient } from '@prisma/client';
import { Runner, RunConfig } from 'openai-agents-js'; // Assuming RunConfig is here or adjust path
import {
  plannerAgent,
  taskDispatcherAgent,
  synthesizerAgent
} from './agents.js';

const prisma = new PrismaClient();
const router = Router();

// Helper to send SSE messages
function sendSse(res, eventName, data) {
  res.write(`data: ${JSON.stringify({ type: eventName, data })}\n\n`);
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

    const history = await prisma.messages.findMany({
      where: { conv_id: conversationId },
      orderBy: { id: 'asc' },
    });
    const historyText = history.map(m => `${m.role}: ${m.content}`).join('\n');
    const runInput = `User Query: ${message}\n\nConversation History:\n${historyText}`;

    const runConfig = new RunConfig({
      // modelProvider: /* If using a custom model provider */,
      // tracingDisabled: false,
      // workflowName: 'MyAgenticWorkflow',
    });

    // 1. Run Planner Agent
    sendSse(res, 'planner_status', { status: 'started' });
    const plannerResult = await Runner.run(plannerAgent, runInput, { runConfig });

    if (plannerResult.error || !plannerResult.finalOutput) {
      sendSse(res, 'error', { message: 'Planner agent failed or produced no output.', details: plannerResult.error?.message || 'Planner produced no output' });
      return res.end();
    }
    
    let plan;
    try {
      plan = JSON.parse(plannerResult.finalOutput);
      sendSse(res, 'planner_status', { status: 'completed', plan });
    } catch (e) {
      sendSse(res, 'error', { message: 'Planner output was not valid JSON.', details: e.message, output: plannerResult.finalOutput });
      return res.end();
    }

    // 2. Run Task Dispatcher Agent (Streaming)
    sendSse(res, 'dispatcher_status', { status: 'started' });
    const dispatcherInput = {
        originalQuery: message,
        plan: plan, // Pass the parsed plan object
        conversationHistory: historyText
    };
    const dispatcherStream = await Runner.runStreamed(taskDispatcherAgent, JSON.stringify(dispatcherInput), { runConfig });
    
    let dispatcherFullOutput = '';
    let collectedTaskResults = [];

    while (true) {
      const event = await dispatcherStream._event_queue.get();
      // TODO: Need to know what `get()` returns when the queue is permanently empty or closed.
      // If it's a specific sentinel (e.g., null, undefined, or a special object), handle it.
      // For now, assuming it always returns a valid event until the stream truly ends.

      // You'll need to inspect the actual structure of `event` from openai-agents-js
      // and map it to meaningful updates for the frontend.
      // Common events: 'llm_delta', 'tool_call_start', 'tool_call_output', 'tool_call_error'
      if (event.type === 'llm_delta' && event.data?.delta) {
        // Dispatcher might have intermediate thoughts or be forming its final JSON output
        // For now, we mostly care about its final structured output.
      } else if (event.type === 'tool_call_start') {
        sendSse(res, 'task_update', { 
          status: 'started', 
          toolName: event.data?.name, 
          toolInput: event.data?.input // or args
        });
      } else if (event.type === 'tool_call_output') {
        sendSse(res, 'task_update', { 
          status: 'completed', 
          toolName: event.data?.name, 
          output: event.data?.output
        });
        // Potentially collect individual task outputs if dispatcher doesn't do it in final output
      } else if (event.type === 'tool_call_error') {
         sendSse(res, 'task_update', { 
          status: 'error', 
          toolName: event.data?.name, 
          error: event.data?.error?.message || 'Tool call failed'
        });
      }
      sendSse(res, 'dispatcher_event', { event }); 
      // Add more event type handlers as needed from the SDK

      if (dispatcherStream.isComplete && dispatcherStream._event_queue.isEmpty()) {
        break;
      }
    }
    
    const dispatcherOutputString = dispatcherStream.finalOutput;
    if (dispatcherOutputString == null) { // Check for null or undefined
      sendSse(res, 'error', { message: 'Task Dispatcher agent failed.', details: 'Task Dispatcher produced no final output string.' });
      return res.end();
    }

    try {
      collectedTaskResults = JSON.parse(dispatcherOutputString);
      sendSse(res, 'dispatcher_status', { status: 'completed', results: collectedTaskResults });
    } catch (e) {
      sendSse(res, 'error', { message: 'Dispatcher output was not valid JSON.', details: e.message, output: dispatcherOutputString });
      return res.end();
    }

    // 3. Run Synthesizer Agent (Streaming)
    sendSse(res, 'synthesizer_status', { status: 'started' });
    const synthesizerInput = {
        originalQuery: message,
        taskResults: collectedTaskResults,
        conversationHistory: historyText
    };
    const synthesizerStream = await Runner.runStreamed(synthesizerAgent, JSON.stringify(synthesizerInput), { runConfig });

    let fullAssistantResponse = '';
    while (true) {
      const event = await synthesizerStream._event_queue.get();
      console.log('BACKEND Orchestrator: Synthesizer event:', JSON.stringify(event)); // DEBUG: Log all synthesizer events
      // Primary handler for true token-by-token streaming from synthesizer
      if (event && event.type === 'agent_text_delta_stream_event' && typeof event.delta === 'string') {
        // console.log('BACKEND Orchestrator: Sending assistant_delta with chunk:', JSON.stringify(event.delta)); // Optional: DEBUG for each chunk
        sendSse(res, 'assistant_delta', { delta: event.delta });
        fullAssistantResponse += event.delta;
      }
      // Fallback or other event types from synthesizer (if any become relevant)
      // else if (event && event.type === 'some_other_synthesizer_event_type') {
      //   // Handle other specific synthesizer events if needed
      // } 
      // The original llm_output and llm_delta cases are removed as they don't match observed synthesizer events for deltas.
      // Handle other synthesizer event types if necessary

      if (synthesizerStream.isComplete && synthesizerStream._event_queue.isEmpty()) {
        break;
      }
    }
    
    // At this point, fullAssistantResponse has been built from deltas.
    // synthesizerStream.finalOutput would ideally be the same if the stream completed fully.
    // No explicit error check on synthesizerStream.finalOutput is strictly needed here if fullAssistantResponse is primary.

    // Save the full response to the database
    if (fullAssistantResponse.trim()) {
      await prisma.messages.create({
        data: { conv_id: conversationId, role: 'assistant', content: fullAssistantResponse },
      });
    }
    sendSse(res, 'synthesizer_status', { status: 'completed' });

  } catch (error) {
    console.error('Orchestrator error:', error);
    sendSse(res, 'error', { message: 'An unexpected error occurred in the orchestrator.', details: error.message });
  } finally {
    sendSse(res, 'done', {});
    res.end();
  }
});

export default router;
