import { Router } from 'express';
import * as prismaClient from '@prisma/client';
import { runDynamicOrchestrator } from './dynamic-bash-orchestrator.js';
import { authenticateToken } from './auth.js';
import { createTaskPlan, updateTaskStatus, getCurrentTasks } from './agents/planning-agent.js';
import { findRelevantMemories, formatMemoriesForContext, generateEmbedding } from './memory-embeddings.js';
import { runMemoryExtraction } from './memory-agent.js';
import { memoryStore } from './memory-store-db.js';
import fs from 'fs/promises';
import path from 'path';

const router = Router();
const { PrismaClient } = prismaClient;
const prisma = new PrismaClient();

/**
 * SSE endpoint for bash orchestrator
 */
router.post('/run', authenticateToken, async (req, res) => {
  console.log('\n========= BASH ORCHESTRATOR API REQUEST =========');
  const { message, conv_id: existing_conv_id } = req.body || {};
  let conversationId = existing_conv_id;
  
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
    
    // Build conversation context
    
    // MEMORY RETRIEVAL DISABLED - Part of temporary memory system disable
    // TODO: Re-enable when memory system is redesigned
    /*
    sendEvent('agent_processing', {
      agent: 'Memory_System',
      message: 'Retrieving relevant memories...'
    });
    
    const relevantMemories = await findRelevantMemories(
      message + (conversationMessages.length > 0 ? '\n' + conversationMessages.slice(-3).map(m => m.content).join('\n') : ''),
      USER_ID,
      3 // Top 3 memories
    );
    
    const memoryContext = formatMemoriesForContext(relevantMemories);
    */
    
    // Create context without memory
    let fullContext;
    if (conversationMessages.length > 0) {
      const history = conversationMessages.map(msg => 
        `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`
      ).join('\n\n');
      fullContext = `Previous conversation:\n${history}\n\nUser: ${message}`;
    } else {
      fullContext = `User: ${message}`;
    }
    
    // MEMORY SYSTEM TEMPORARILY DISABLED
    // TODO: Re-implement memory system with better architecture:
    // 1. Use a queue system to prevent concurrent memory operations
    // 2. Implement proper cancellation tokens
    // 3. Add circuit breaker pattern to prevent infinite retries
    // 4. Consider using a separate service/worker for memory operations
    console.log('[Memory] System temporarily disabled - needs redesign');
    
    // Check if request needs planning (complex or multi-step)
    const needsPlanning = analyzeComplexity(message);
    
    if (needsPlanning) {
      sendEvent('agent_processing', {
        agent: 'Planning_Agent',
        message: 'Creating task plan...'
      });
      
      // Create task plan
      const planResult = await createTaskPlan(message, conversationId.toString());
      
      if (planResult.success && planResult.tasks.length > 0) {
        // Send task summary to frontend
        sendEvent('task_summary', {
          tasks: planResult.tasks.map((task, index) => ({
            id: `task_${conversationId}_${index}`,
            content: task.title || task,
            status: task.status || 'pending',
            conversation_id: conversationId
          })),
          conversation_id: conversationId
        });
        
        // Also send task_plan_created event for TaskMarkdownDisplay
        try {
          const planPath = path.join(__dirname, 'plans', `TODO-${conversationId}.md`);
          const planContent = await fs.readFile(planPath, 'utf-8');
          console.log('[Bash Orchestrator] Sending task_plan_created event for conversation:', conversationId);
          console.log('[Bash Orchestrator] Plan content length:', planContent.length);
          sendEvent('task_plan_created', {
            markdown: planContent,
            filename: `TODO-${conversationId}.md`,
            taskCount: planResult.tasks.length,
            conversation_id: conversationId
          });
        } catch (err) {
          console.log('[Bash Orchestrator] Could not read plan file:', err.message);
        }
      }
    }
    
    // Run orchestrator with full context
    sendEvent('agent_processing', {
      agent: 'Dynamic_Bash_Orchestrator',
      message: 'Analyzing request and executing tasks...'
    });
    
    // Start task progress monitoring if we have tasks
    let taskMonitorInterval;
    if (needsPlanning) {
      taskMonitorInterval = setInterval(async () => {
        try {
          const currentTasks = await getCurrentTasks(conversationId.toString());
          if (currentTasks.success) {
            sendEvent('task_summary', {
              tasks: currentTasks.tasks.map((task, index) => ({
                id: `task_${conversationId}_${index}`,
                content: task.title || task,
                status: task.status || 'pending',
                conversation_id: conversationId
              })),
              conversation_id: conversationId
            });
            
            // Also send the markdown update
            try {
              const planPath = path.join(__dirname, 'plans', `TODO-${conversationId}.md`);
              const planContent = await fs.readFile(planPath, 'utf-8');
              sendEvent('task_plan_created', {
                markdown: planContent,
                filename: `TODO-${conversationId}.md`,
                taskCount: currentTasks.tasks.length,
                conversation_id: conversationId
              });
            } catch (err) {
              // Ignore if file doesn't exist
            }
          }
        } catch (error) {
          console.error('Error monitoring tasks:', error);
        }
      }, 2000); // Check every 2 seconds
    }
    
    const result = await runDynamicOrchestrator(fullContext, {
      conversationId,
      sseEmitter: sendEvent,
      taskUpdater: needsPlanning ? async (taskIndex, status) => {
        await updateTaskStatus(conversationId.toString(), taskIndex, status);
      } : null
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
    if (textResponse) {
      console.log('=== SENDING AGENT_MESSAGE EVENT ===');
      console.log('Content:', textResponse.substring(0, 100) + '...');
      sendEvent('agent_message', {
        agent: 'Dynamic_Bash_Orchestrator',
        content: textResponse,
        timestamp: new Date().toISOString()
      });
      console.log('=== AGENT_MESSAGE EVENT SENT ===');
      
      // MEMORY SAVE DISABLED - Part of temporary memory system disable
      // TODO: Re-enable when memory system is redesigned
    } else {
      console.log('=== WARNING: No textResponse to send ===');
    }
    
    // Send completion
    sendEvent('done', {
      finalResponse: textResponse || 'No response generated',
      conversationId
    });
    
  } catch (error) {
    console.error('Bash orchestrator API error:', error);
    sendEvent('error', {
      message: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  } finally {
    res.end();
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

export default router;