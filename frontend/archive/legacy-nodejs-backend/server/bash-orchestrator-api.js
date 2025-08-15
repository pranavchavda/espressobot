import { Router } from 'express';
import { db } from './config/database.js';

const prisma = db;
import { runDynamicOrchestrator } from './espressobot1.js';
import { authenticateToken } from './auth.js';
import { createTaskPlan, updateTaskStatus, getCurrentTasks } from './agents/task-planning-agent.js';
import { memoryOperations } from './memory/memory-operations-local.js';
import { buildCompressedContext } from './agents/conversation-summarizer-agent.js';
import fs from 'fs/promises';
import path from 'path';

const router = Router();

// Store AbortController instances per conversation for interrupt functionality
const conversationAbortControllers = new Map();

/**
 * SSE endpoint for bash orchestrator
 */
router.post('/run', authenticateToken, async (req, res) => {
  console.log('\n========= BASH ORCHESTRATOR API REQUEST =========');
  const { message, conv_id: existing_conv_id, image, file } = req.body || {};
  let conversationId = existing_conv_id;
  
  // Debug logging for image data
  if (image) {
    console.log('[DEBUG] Image data received:', {
      type: image.type,
      hasData: !!image.data,
      hasUrl: !!image.url,
      dataLength: image.data ? image.data.length : 0
    });
  } else {
    console.log('[DEBUG] No image data in request');
  }
  
  // Debug logging for file data
  if (file) {
    console.log('[DEBUG] File data received:', {
      type: file.type,
      name: file.name,
      size: file.size,
      encoding: file.encoding,
      hasContent: !!file.content,
      hasData: !!file.data,
      contentLength: file.content ? file.content.length : 0,
      dataLength: file.data ? file.data.length : 0
    });
  } else {
    console.log('[DEBUG] No file data in request');
  }
  
  // Setup SSE
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();
  
  const sendEvent = (event, data) => {
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
    // Force flush to ensure events are sent immediately
    if (res.flush) res.flush();
  };
  
  try {
    // Handle conversation - get user ID from authenticated request
    const USER_ID = req.user?.id || 1;
    
    if (!conversationId) {
      const conversation = await prisma.conversations.create({
        data: {
          user_id: USER_ID,
          title: message.substring(0, 100),
          filename: `bash-conversation-${Date.now()}.json`,
          created_at: new Date(),
          updated_at: new Date()
        }
      });
      conversationId = conversation.id;
      console.log('Created new conversation:', conversationId);
    }
    
    sendEvent('start', { message: 'Bash orchestrator initialized' });
    sendEvent('conversation_id', { conv_id: conversationId });
    
    // Load conversation history from messages table
    const conversationMessages = await prisma.messages.findMany({
      where: { conv_id: parseInt(conversationId) },
      orderBy: { created_at: 'asc' }
    });
    
    // Store user message
    await prisma.messages.create({
      data: {
        conv_id: conversationId,
        role: 'user',
        content: message,
        created_at: new Date()
      }
    });
    
    // Make SSE emitter and conversation ID globally available for tools
    global.currentSseEmitter = sendEvent;
    global.currentConversationId = conversationId;
    
    // Build conversation context
    // Note: Memories will be handled by the smart context loading system to avoid duplication
    
    // Store the user ID globally for memory operations
    global.currentUserId = `user_${USER_ID}`;
    
    // Create context with conversation compression
    let fullContext;
    if (conversationMessages.length > 0) {
      console.log(`[CONTEXT] Processing ${conversationMessages.length} messages with compression`);
      
      // Use the summarization agent to build compressed context
      const compressedContext = await buildCompressedContext(conversationMessages, {
        maxRecentTurns: 8  // Keep last 8 messages unsummarized
      });
      
      // Build context string with summaries and recent messages
      let contextParts = [`[Conversation ID: ${conversationId}]`];
      
      // Add conversation summary if available
      if (compressedContext.finalSummary) {
        contextParts.push(`\nConversation Summary (${compressedContext.summarizedCount} earlier messages):\n${compressedContext.finalSummary.summary}`);
        
        // Add pending items if any
        if (compressedContext.finalSummary.pendingItems?.length > 0) {
          contextParts.push(`\nPending items from earlier conversation:\n- ${compressedContext.finalSummary.pendingItems.join('\n- ')}`);
        }
      }
      
      // Add recent conversation
      if (compressedContext.recentMessages.length > 0) {
        const recentHistory = compressedContext.recentMessages.map(msg => {
          // Still truncate individual messages if they're very long
          const content = msg.content.length > 5000 ? 
            msg.content.substring(0, 5000) + '\n[Message truncated for size]' : 
            msg.content;
          return `${msg.role === 'user' ? 'User' : 'Assistant'}: ${content}`;
        }).join('\n\n');
        
        contextParts.push(`\nRecent conversation:\n${recentHistory}`);
      }
      
      // Add current message
      contextParts.push(`\nUser: ${message}`);
      
      fullContext = contextParts.join('\n');
      
      // Log compression statistics
      console.log(`[CONTEXT COMPRESSION] Summary: ${compressedContext.summarizedCount} messages compressed, ${compressedContext.recentMessages.length} recent messages kept`);
      console.log(`[CONTEXT SIZE] Compressed context: ${fullContext.length} characters (${(fullContext.length/1024).toFixed(1)}KB)`);
    } else {
      fullContext = `[Conversation ID: ${conversationId}]\n\nUser: ${message}`;
    }
    
    // Add image data to context if present
    if (image) {
      // Store image data globally for the orchestrator to access
      global.currentImageData = image;
    }
    
    // Add file data to context if present
    if (file) {
      // Store file data globally for the orchestrator to access
      global.currentFileData = file;
    }
    
    // REMOVED: Automatic task planning based on simple pattern matching
    // Task planning is now orchestrator-driven through the task_planner tool
    // This ensures planning happens with full context when the orchestrator decides it's needed
    
    // Run orchestrator with full context
    sendEvent('agent_processing', {
      agent: 'EspressoBot1',
      message: 'Analyzing request and executing tasks...'
    });
    
    // Start task progress monitoring
    let taskMonitorInterval;
    // Check periodically if tasks exist for this conversation
    taskMonitorInterval = setInterval(async () => {
      try {
        const currentTasks = await getCurrentTasks(conversationId.toString());
        if (currentTasks.success && currentTasks.tasks && currentTasks.tasks.length > 0) {
          // Only send task_summary for live status updates
          sendEvent('task_summary', {
            tasks: currentTasks.tasks.map((task, index) => ({
              id: `task_${conversationId}_${index}`,
              content: task.title || task.description || task,
              status: task.status || 'pending',
              conversation_id: conversationId
            })),
            conversation_id: conversationId
          });
        }
      } catch (error) {
        console.error('Error monitoring tasks:', error);
      }
    }, 2000); // Check every 2 seconds
    
    // Create AbortController for this conversation
    const abortController = new AbortController();
    console.log(`[ORCHESTRATOR] Storing AbortController for conversation: ${conversationId} (type: ${typeof conversationId})`);
    conversationAbortControllers.set(conversationId, abortController);
    console.log(`[ORCHESTRATOR] Total stored controllers: ${conversationAbortControllers.size}`);
    console.log(`[ORCHESTRATOR] Stored controller keys:`, Array.from(conversationAbortControllers.keys()));
    
    // Run the orchestrator
    console.log('*** RUNNING ORCHESTRATOR ***');
    const result = await runDynamicOrchestrator(fullContext, {
      conversationId,
      userId: USER_ID,
      sseEmitter: sendEvent,
      taskUpdater: async (taskIndex, status) => {
        await updateTaskStatus(conversationId.toString(), taskIndex, status);
      },
      abortSignal: abortController.signal
    });
    
    // Stop task monitoring
    if (taskMonitorInterval) {
      clearInterval(taskMonitorInterval);
    }
    
    // Not using streaming, no need to wait for completion
    
    // Extract text response from RunResult for database storage
    let textResponse = '';
    
    // Debug result structure
    console.log('=== BASH ORCHESTRATOR RESULT ===');
    console.log('Result type:', typeof result);
    console.log('Result keys:', result ? Object.keys(result) : 'null');
    console.log('Has finalOutput:', result?.finalOutput ? 'YES' : 'NO');
    console.log('finalOutput value:', result?.finalOutput ? result.finalOutput.substring(0, 100) + '...' : 'NONE');
    console.log('Has state:', result?.state ? 'YES' : 'NO');
    
    // Log all state keys and their values
    if (result?.state) {
      console.log('\n=== STATE DETAILS ===');
      const state = result.state;
      
      // Log each state property
      console.log('_currentTurn:', state._currentTurn);
      console.log('_currentAgent:', state._currentAgent?.name || 'null');
      console.log('_originalInput:', typeof state._originalInput === 'string' ? 
        state._originalInput.substring(0, 100) + '...' : state._originalInput);
      console.log('_modelResponses:', Array.isArray(state._modelResponses) ? 
        `Array(${state._modelResponses.length})` : state._modelResponses);
      console.log('_currentAgentSpan:', state._currentAgentSpan);
      console.log('_context:', state._context ? Object.keys(state._context) : 'null');
      console.log('_toolUseTracker:', state._toolUseTracker);
      console.log('_generatedItems:', Array.isArray(state._generatedItems) ? 
        `Array(${state._generatedItems.length})` : state._generatedItems);
      console.log('_maxTurns:', state._maxTurns);
      console.log('_noActiveAgentRun:', state._noActiveAgentRun);
      console.log('_lastTurnResponse:', state._lastTurnResponse ? 
        Object.keys(state._lastTurnResponse) : 'null');
      console.log('_inputGuardrailResults:', state._inputGuardrailResults);
      console.log('_outputGuardrailResults:', state._outputGuardrailResults);
      console.log('_currentStep:', state._currentStep ? {
        type: state._currentStep.type,
        output: state._currentStep.output ? 
          state._currentStep.output.substring(0, 100) + '...' : 'null'
      } : 'null');
      console.log('_lastProcessedResponse:', state._lastProcessedResponse ? 
        Object.keys(state._lastProcessedResponse) : 'null');
      console.log('_trace:', state._trace ? {
        id: state._trace.id,
        workflow_name: state._trace.workflow_name
      } : 'null');
      console.log('====================');
    }
    
    console.log('================================');
    
    // With streaming enabled, use finalOutput like unified orchestrator
    if (result && result.finalOutput) {
      textResponse = result.finalOutput;
    } else if (result && result.state) {
      // Fallback to old method
      const lastStep = result.state._currentStep;
      if (lastStep && lastStep.output) {
        textResponse = lastStep.output;
      } else {
        // Fallback to generated items
        const generatedItems = result.state._generatedItems || [];
        const messageOutputs = generatedItems.filter(item => item.type === 'message_output');
        if (messageOutputs.length > 0) {
          textResponse = messageOutputs[messageOutputs.length - 1].content;
        }
      }
    } else if (typeof result === 'string') {
      textResponse = result;
    }
    
    // Store assistant response
    await prisma.messages.create({
      data: {
        conv_id: conversationId,
        role: 'assistant',
        content: textResponse || 'No response generated',
        created_at: new Date()
      }
    });
    
    // Send the final response as agent_message event (like multi-agent orchestrator)
    // Always send agent_message to prevent frontend hanging
    const finalResponse = textResponse || 'I apologize, but I encountered an issue processing your request. Please try again.';
    
    console.log('=== SENDING AGENT_MESSAGE EVENT ===');
    console.log('Content:', finalResponse.substring(0, 100) + '...');
    sendEvent('agent_message', {
      agent: 'EspressoBot1',
      content: finalResponse,
      timestamp: new Date().toISOString()
    });
    console.log('=== AGENT_MESSAGE EVENT SENT ===');
    
    // Store conversation in memory for future retrieval (non-blocking) - only if we have real response
    if (textResponse) {
      // Use setImmediate to ensure response is sent first
      setImmediate(async () => {
        try {
          // Create conversation summary for memory extraction
          const conversationSummary = `User: ${message}\nAssistant: ${textResponse}`;
          
          console.log(`[Memory] Extracting facts for conversation ${conversationId}`);
          console.log(`[Memory] Message: "${message.substring(0, 100)}..."`);
          console.log(`[Memory] Response: "${textResponse.substring(0, 100)}..."`);
          
          // Use actual user ID for cross-conversation memory persistence
          const memoryUserId = `user_${USER_ID}`;
          
          // Extract facts using GPT-4.1-mini
          const extractedFacts = await memoryOperations.extractMemorySummary(conversationSummary, {
            conversationId: conversationId.toString(),
            agent: 'EspressoBot1'
          });
        
        console.log(`[Memory] Extracted ${extractedFacts.length} facts`);
        
        // Store each extracted fact as a separate memory
        let successCount = 0;
        for (const fact of extractedFacts) {
          try {
            const memoryAddResult = await memoryOperations.add(
              fact.content,
              memoryUserId,
              fact.metadata
            );
            
            if (memoryAddResult.success) {
              successCount++;
              console.log(`[Memory] Stored fact: "${fact.content.substring(0, 50)}..."`);
            }
          } catch (factError) {
            console.error(`[Memory] Error storing fact:`, factError);
          }
        }
        
          console.log(`[Memory] Successfully stored ${successCount}/${extractedFacts.length} facts`);
          
        } catch (error) {
          console.error('[Memory] Error extracting/storing memory:', error);
          // Continue even if memory storage fails
        }
      });
    } else {
      console.log('=== WARNING: No textResponse - sending fallback message ===');
    }
    
    // Send completion
    console.log('[ORCHESTRATOR] Sending done event');
    sendEvent('done', {
      finalResponse: finalResponse,
      conversationId
    });
    console.log('[ORCHESTRATOR] Done event sent');
    
  } catch (error) {
    console.error('Bash orchestrator API error:', error);
    sendEvent('error', {
      message: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  } finally {
    // Clear memory cache to prevent leaks
    memoryOperations.clearCache();
    
    // Clean up globals and abort controller
    global.currentSseEmitter = null;
    global.currentConversationId = null;
    global.currentImageData = null;
    global.currentFileData = null;
    console.log(`[ORCHESTRATOR] Cleaning up AbortController for conversation: ${conversationId}`);
    conversationAbortControllers.delete(conversationId);
    conversationAbortControllers.delete(parseInt(conversationId));
    conversationAbortControllers.delete(String(conversationId));
    console.log(`[ORCHESTRATOR] Calling res.end() for conversation: ${conversationId}`);
    // Send a final newline to ensure the stream is properly terminated
    res.write('\n');
    res.end();
    console.log(`[ORCHESTRATOR] res.end() completed for conversation: ${conversationId}`);
  }
});

/**
 * POST /interrupt - Interrupt ongoing agent execution
 */
router.post('/interrupt', authenticateToken, async (req, res) => {
  console.log('\n========= INTERRUPT REQUEST =========');
  const { conv_id } = req.body || {};
  
  if (!conv_id) {
    return res.status(400).json({ error: 'Conversation ID is required' });
  }
  
  console.log('Attempting to interrupt conversation:', conv_id, '(type:', typeof conv_id, ')');
  console.log('Available controller keys:', Array.from(conversationAbortControllers.keys()));
  console.log('Total controllers:', conversationAbortControllers.size);
  
  // Try both string and number forms of the conversation ID
  let abortController = conversationAbortControllers.get(conv_id);
  if (!abortController) {
    abortController = conversationAbortControllers.get(parseInt(conv_id));
    console.log('Trying parseInt version:', parseInt(conv_id));
  }
  if (!abortController) {
    abortController = conversationAbortControllers.get(String(conv_id));
    console.log('Trying String version:', String(conv_id));
  }
  
  if (abortController) {
    console.log('Found AbortController for conversation:', conv_id, '- sending abort signal');
    abortController.abort('User requested interruption');
    
    // Clean up the controller (try all possible keys)
    conversationAbortControllers.delete(conv_id);
    conversationAbortControllers.delete(parseInt(conv_id));
    conversationAbortControllers.delete(String(conv_id));
    
    res.json({ success: true, message: 'Interrupt signal sent' });
  } else {
    console.log('No active AbortController found for conversation:', conv_id);
    console.log('Available keys were:', Array.from(conversationAbortControllers.keys()));
    res.json({ success: false, message: 'No active execution found for this conversation' });
  }
});

// Function to analyze if a request needs planning
function analyzeComplexity(message) {
  const complexityIndicators = [
    // Multi-step indicators
    'and then', 'after that', 'followed by', 'next', 'finally',
    'first', 'second', 'third', 'step', 'steps',
    
    // Bulk operation indicators
    'all', 'every', 'each', 'multiple', 'bulk', 'batch',
    'all products', 'all items', 'everything',
    
    // Complex action indicators
    'create.*bundle', 'create.*combo', 'update.*prices',
    'sync', 'migrate', 'analyze', 'report', 'compare',
    'find.*and.*update', 'search.*and.*modify',
    
    // Conditional indicators
    'if', 'when', 'unless', 'except', 'but not',
    
    // Multiple entity indicators
    'products', 'items', 'variants', 'collections'
  ];
  
  const lowerMessage = message.toLowerCase();
  
  // Check for multiple actions in one request
  const actionWords = ['create', 'update', 'delete', 'find', 'search', 'modify', 'add', 'remove', 'change'];
  const actionCount = actionWords.filter(action => lowerMessage.includes(action)).length;
  
  // Check for complexity indicators
  const hasComplexityIndicator = complexityIndicators.some(indicator => {
    if (indicator.includes('.*')) {
      // Handle regex patterns
      const regex = new RegExp(indicator, 'i');
      return regex.test(lowerMessage);
    }
    return lowerMessage.includes(indicator);
  });
  
  // Check message length (longer messages often indicate complex requests)
  const isLongMessage = message.length > 100;
  
  // Check for numbered lists
  const hasNumberedList = /\d+[\.\)]/g.test(message);
  
  return actionCount >= 2 || hasComplexityIndicator || isLongMessage || hasNumberedList;
}

/**
 * GET /logs - Server-Sent Events endpoint for streaming logs
 */
router.get('/logs', async (req, res) => {
  // Get token from query params for SSE (EventSource doesn't support headers)
  const token = req.query.token;
  
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  
  // Manually verify token
  try {
    const jwt = await import('jsonwebtoken');
    const decoded = jwt.default.verify(token, process.env.JWT_SECRET || 'your-secret-key');
    req.user = decoded;
  } catch (error) {
    return res.status(401).json({ error: 'Invalid token' });
  }
  
  const { logStreamer } = await import('./services/log-streamer.js');
  const userId = `user_${req.user?.id || 1}`;
  
  console.log(`[LogStreamer] New SSE connection for ${userId}`);
  
  // Add this client to the log streamer
  logStreamer.addClient(userId, res);
  
  // Handle client disconnect
  req.on('close', () => {
    console.log(`[LogStreamer] SSE connection closed for ${userId}`);
  });
});

/**
 * Endpoint to queue messages for injection during active agent execution
 */
router.post('/inject-message', authenticateToken, async (req, res) => {
  const { conversationId, message, priority = 'normal' } = req.body;
  
  if (!conversationId || !message) {
    return res.status(400).json({
      error: 'conversationId and message are required'
    });
  }
  
  try {
    // Import message injector
    const { messageInjector } = await import('./utils/agent-message-injector.js');
    
    // Check if agent is running for this conversation
    const agentState = messageInjector.getAgentState(conversationId);
    
    if (!agentState.isRunning) {
      return res.status(400).json({
        error: 'No active agent execution for this conversation',
        state: agentState
      });
    }
    
    // Queue the message
    const messageId = messageInjector.queueMessage(conversationId, message, priority);
    
    console.log(`[API] Queued message for injection in conversation ${conversationId}: "${message.substring(0, 50)}..."`);
    
    res.json({
      success: true,
      messageId,
      agentState,
      queueLength: messageInjector.getPendingMessages(conversationId).length
    });
    
  } catch (error) {
    console.error('[API] Error queuing message for injection:', error);
    res.status(500).json({
      error: 'Failed to queue message',
      details: error.message
    });
  }
});

/**
 * Get injection status for a conversation
 */
router.get('/injection-status/:conversationId', authenticateToken, async (req, res) => {
  const { conversationId } = req.params;
  
  try {
    const { messageInjector } = await import('./utils/agent-message-injector.js');
    
    const agentState = messageInjector.getAgentState(conversationId);
    const pendingMessages = messageInjector.getPendingMessages(conversationId);
    
    res.json({
      conversationId,
      agentState,
      pendingMessages: pendingMessages.length,
      canInject: messageInjector.canInject(conversationId),
      messages: pendingMessages
    });
    
  } catch (error) {
    console.error('[API] Error getting injection status:', error);
    res.status(500).json({
      error: 'Failed to get injection status',
      details: error.message
    });
  }
});

export default router;