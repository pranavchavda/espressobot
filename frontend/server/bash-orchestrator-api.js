import { Router } from 'express';
import * as prismaClient from '@prisma/client';
import { runDynamicOrchestrator } from './dynamic-bash-orchestrator.js';
import { authenticateToken } from './auth.js';

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
    let fullContext = '';
    if (conversationMessages.length > 0) {
      const history = conversationMessages.map(msg => 
        `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`
      ).join('\n\n');
      fullContext = `Previous conversation:\n${history}\n\nUser: ${message}`;
    } else {
      fullContext = message;
    }
    
    // Run orchestrator with full context
    sendEvent('agent_processing', {
      agent: 'Dynamic_Bash_Orchestrator',
      message: 'Analyzing request and planning tasks...'
    });
    
    const result = await runDynamicOrchestrator(fullContext, {
      conversationId,
      sseEmitter: sendEvent
    });
    
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

export default router;