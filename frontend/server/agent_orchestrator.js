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

    const history = await prisma.messages.findMany({
      where: { conv_id: conversationId },
      orderBy: { id: 'asc' },
    });
    let plannerInputMessages = history.map(m => ({
      type: 'message',
      role: m.role, // 'user' or 'assistant'
      // Truncate long assistant messages in history for the agent input
      content: m.content
    }));

    const { image } = req.body;
    let currentUserMessageContent;

    console.log('BACKEND Orchestrator: Full request body:', JSON.stringify(req.body, null, 2));
    console.log('BACKEND Orchestrator: Image object:', JSON.stringify(image, null, 2));
    console.log('BACKEND Orchestrator: Message text:', JSON.stringify(message));

    if (image && (image.url || image.data)) {
      const imageUrl = image.type === 'data_url' ? image.data : image.url;
      console.log('BACKEND Orchestrator: Final imageUrl:', imageUrl?.substring(0, 100) + '...');
      console.log('BACKEND Orchestrator: Creating multimodal content with message:', JSON.stringify(message));
      
      const textPart = {
        type: 'input_text',
        text: message || '' // Ensure text is never undefined
      };
      const imagePart = {
        type: 'input_image',
        image_url: imageUrl,
        detail: process.env.VISION_DETAIL || 'auto'
      };
      
      console.log('BACKEND Orchestrator: Created textPart:', JSON.stringify(textPart));
      console.log('BACKEND Orchestrator: Created imagePart:', JSON.stringify(imagePart, null, 2));
      
      currentUserMessageContent = [textPart, imagePart];
    } else {
      currentUserMessageContent = message; // Simple string for text-only
    }

    // Replace the last message with multimodal content if we have an image
    if (image && (image.url || image.data)) {
      plannerInputMessages[plannerInputMessages.length - 1] = {
        type: 'message',
        role: 'user',
        content: currentUserMessageContent
      };
    } else {
      plannerInputMessages.push({
        type: 'message',
        role: 'user',
        content: currentUserMessageContent
      });
    }

    const plannerInput = plannerInputMessages;
    console.log('BACKEND Orchestrator: Sending to planner:', JSON.stringify(plannerInput, null, 2));
    
    // Additional debug: Check the last message specifically
    const lastMessage = plannerInput[plannerInput.length - 1];
    console.log('BACKEND Orchestrator: Last message to planner:', JSON.stringify(lastMessage, null, 2));
    if (Array.isArray(lastMessage.content)) {
      console.log('BACKEND Orchestrator: Multimodal message parts:', lastMessage.content.length);
      lastMessage.content.forEach((part, i) => {
        console.log(`BACKEND Orchestrator: Part ${i} full object:`, JSON.stringify(part, null, 2));
        if (part.type === 'input_text') {
          console.log(`BACKEND Orchestrator: Text content: "${part.text}"`);
        } else if (part.type === 'input_image') {
          console.log(`BACKEND Orchestrator: Image URL prefix: ${part.image_url?.substring(0, 50)}...`);
        }
      });
    }
    // The plannerAgent's system prompt will need to be aware that it's receiving a full message history
    // and the user's query is the last message. It should extract context accordingly.
    // It no longer gets a single string with "User Query: ... Conversation History: ..."
    // Instead, it gets an array of message objects.

    // For the other agents (dispatcher, synthesizer), they still expect a JSON.stringified object
    // containing originalQuery, conversationHistory (as a string), etc.
    // We need to reconstruct historyText for them.
    const historyText = history.map(m => {
      if (m.role === 'assistant' && m.content.length > 500) {
        return `${m.role}: ${m.content.substring(0, 497)}...`;
      }
      return `${m.role}: ${m.content}`;
    }).join('\n');

    const runConfig = new RunConfig({
      // modelProvider: /* If using a custom model provider */,
      // tracingDisabled: false,
      // workflowName: 'MyAgenticWorkflow',
    });

    // 1. Run Planner Agent
    sendSse(res, 'planner_status', { status: 'started' });
    const plannerResult = await Runner.run(plannerAgent, plannerInput, { runConfig });

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
      } else if (event.type === 'tool_call_started') {
        console.log("BACKEND Orchestrator: Raw tool_call_started event from SDK:", JSON.stringify(event, null, 2));
        const toolCallId = event.toolCallId || `unknown_id_${Date.now()}`;
        const toolName = event.toolName || "Unknown Tool";
        const toolInput = event.toolInput !== undefined ? event.toolInput : "No input";
        sendSse(res, 'dispatcher_event', { 
          type: event.type, // Forwarding original type for potential frontend use
          tool_call_id: toolCallId,
          tool_name: toolName, 
          tool_input: toolInput,
          status: 'started'
        });
      } else if (event.type === 'tool_call_completed') {
        console.log("BACKEND Orchestrator: Raw tool_call_completed event from SDK:", JSON.stringify(event, null, 2));
        const toolCallId = event.toolCallId || `unknown_id_${Date.now()}`;
        const toolName = event.toolName || "Unknown Tool"; // Fallback if not present
        collectedTaskResults.push({ toolCallId: toolCallId, output: event.output });
        sendSse(res, 'dispatcher_event', {
          type: event.type,
          tool_call_id: toolCallId,
          tool_name: toolName, 
          output: event.output,
          status: 'completed'
        });
        // Potentially collect individual task outputs if dispatcher doesn't do it in final output
      } else if (event.type === 'tool_call_failed') {
        console.log("BACKEND Orchestrator: Raw tool_call_failed event from SDK:", JSON.stringify(event, null, 2));
        const toolCallId = event.toolCallId || `unknown_id_${Date.now()}`;
        const toolName = event.toolName || "Unknown Tool"; // Fallback if not present
        collectedTaskResults.push({ toolCallId: toolCallId, error: event.error?.message || event.error });
        sendSse(res, 'dispatcher_event', {
          type: event.type,
          tool_call_id: toolCallId,
          tool_name: toolName, 
          error: event.error?.message || event.error || 'Tool call failed',
          status: 'error'
        });
      } else if (event.type === 'llm_output') {
        // This might be the dispatcher's own reasoning or summary before/after tools
        // For now, we're not sending this as a specific dispatcher_event to update tasks
        // but you could if it's relevant to the UI.
        // console.log('Dispatcher LLM Output:', event.output);
      } else {
        // Forward other dispatcher events if necessary, or log them
        // console.log('Unhandled dispatcher event:', event);
      }
      // Add more event type handlers as needed from the SDK. 
      // The generic sendSse(res, 'dispatcher_event', { event }); has been removed.

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
