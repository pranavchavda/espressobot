import express from 'express';
import { run } from '@openai/agents';
import { espressoBotOrchestrator } from './agents/espressobot-orchestrator.js';
// import { simpleOrchestrator as espressoBotOrchestrator } from './agents/simple-orchestrator.js';
import EventEmitter from 'events';
import { PrismaClient } from '@prisma/client';

const router = express.Router();
const prisma = new PrismaClient();

// Event emitter for SSE
class SSEEmitter extends EventEmitter {}

// Main orchestrator endpoint
router.post('/run', async (req, res) => {
  const { conv_id, message, forceTaskGen, imageData, imageUrl } = req.body;
  
  // Set up SSE
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*',
  });

  const sseEmitter = new SSEEmitter();
  
  // Helper to send SSE events
  const sendEvent = (eventName, data) => {
    console.log(`[MULTI-AGENT] Sending SSE event: ${eventName}`, data);
    res.write(`event: ${eventName}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  // Helper to get agent-specific status messages
  const getAgentStatusMessage = (agentName, toolName = null) => {
    const messages = {
      'EspressoBot_Orchestrator': {
        default: 'EspressoBot Orchestrator is analyzing your request...',
        'transfer_to_Memory_Agent': 'EspressoBot is routing to Memory Agent...',
        'transfer_to_Task_Planner_Agent': 'EspressoBot is routing to Task Planner...',
        'transfer_to_Product_Creation_Agent': 'EspressoBot is routing to Product Creation Agent...',
        'transfer_to_Product_Update_Agent': 'EspressoBot is routing to Product Update Agent...'
      },
      'Memory_Agent': {
        default: 'Memory Agent is retrieving relevant memories...',
        'search_memories': 'Memory Agent is searching through conversation history...',
        'store_memory': 'Memory Agent is storing important information...',
        'transfer_to_EspressoBot_Orchestrator': 'Memory Agent is returning to orchestrator...'
      },
      'Task_Planner_Agent': {
        default: 'Task Planner is creating an execution plan...',
        'create_task_plan': 'Task Planner is structuring your tasks...',
        'update_task_status': 'Task Planner is updating task progress...',
        'get_current_tasks': 'Task Planner is retrieving current tasks...',
        'transfer_to_EspressoBot_Orchestrator': 'Task Planner is handing off for execution...'
      },
      'Product_Creation_Agent': {
        default: 'Product Creation Agent is creating products...',
        'product_create_full': 'Creating new product listing...',
        'create_combo': 'Creating combo product bundle...',
        'create_open_box': 'Creating open box listing...',
        'transfer_to_EspressoBot_Orchestrator': 'Product Creation Agent is returning results...'
      },
      'Product_Update_Agent': {
        default: 'Product Update Agent is searching for products...',
        'search_products': 'Searching product catalog...',
        'get_product': 'Retrieving product details...',
        'update_pricing': 'Updating product prices...',
        'manage_tags': 'Managing product tags...',
        'transfer_to_EspressoBot_Orchestrator': 'Product Update Agent is returning results...'
      }
    };
    
    const agentMessages = messages[agentName] || { default: `${agentName} is processing...` };
    if (toolName && agentMessages[toolName]) {
      return agentMessages[toolName];
    }
    return agentMessages.default;
  };

  // Send initial event
  sendEvent('start', { message: 'Multi-agent system initialized' });

  let conversationId = conv_id;
  const USER_ID = 1; // Default user ID, same as unified orchestrator
  
  try {
    // Handle conversation creation/retrieval
    if (conversationId) {
      // Check if conversation exists
      const conversation = await prisma.conversations.findUnique({
        where: { id: conversationId }
      });
      
      if (!conversation) {
        console.log('Conversation not found, creating new one');
        conversationId = null;
      } else {
        console.log('Found existing conversation:', conversationId);
      }
    }
    
    // Create new conversation if needed
    if (!conversationId) {
      const conversation = await prisma.conversations.create({
        data: {
          user_id: USER_ID,
          title: message.substring(0, 100),
          filename: `conversation-${Date.now()}.json`,
          created_at: new Date(),
          updated_at: new Date()
        }
      });
      conversationId = conversation.id;
      console.log('Created new conversation:', conversationId);
    }
    
    // Send conversation ID to client
    sendEvent('conversation_id', { conv_id: conversationId });
    
    // Load conversation history from messages table
    const conversationMessages = await prisma.messages.findMany({
      where: { conv_id: parseInt(conversationId) },
      orderBy: { created_at: 'asc' }
    });
    
    let messages = conversationMessages.map(msg => ({
      role: msg.role,
      content: msg.content
    }));
    
    // Prepare the user message
    let userMessage = message;
    if (imageData || imageUrl) {
      userMessage = {
        role: 'user',
        content: [
          { type: 'text', text: message }
        ]
      };
      
      if (imageData) {
        userMessage.content.push({
          type: 'image',
          image: imageData
        });
      } else if (imageUrl) {
        userMessage.content.push({
          type: 'image_url',
          image_url: { url: imageUrl }
        });
      }
    }
    
    // Add user message to history
    messages.push({ role: 'user', content: userMessage });

    // Context object to pass between agents
    const context = {
      conversationId,
      forceTaskGen,
      sseEmitter,
      memories: [],
      tasks: [],
      results: {}
    };

    // Build agent input string (similar to unified orchestrator)
    let agentInput = message;
    
    // Add conversation history if available
    if (messages.length > 1) {
      const historyText = messages.slice(0, -1)
        .map(m => `${m.role === 'user' ? 'User' : 'Assistant'}: ${typeof m.content === 'object' ? JSON.stringify(m.content) : m.content}`)
        .join('\n');
      agentInput = `Previous conversation:\n${historyText}\n\nUser: ${message}`;
    }
    
    // Add conversation ID to the input for task planning
    agentInput = `[Conversation ID: ${conversationId}]\n${agentInput}`;
    
    let result;
    try {
      console.log('[MULTI-AGENT] Starting agent run with input:', agentInput.substring(0, 100) + '...');
      result = await run(espressoBotOrchestrator, agentInput, {
        maxTurns: 10,
        context,
        onStepStart: (step) => {
          console.log('[MULTI-AGENT] onStepStart called:', step.type, step.agent?.name);
          const agentName = step.agent?.name || 'Unknown';
          
          if (step.type === 'handoff') {
          sendEvent('handoff', {
            from: step.fromAgent?.name || 'Unknown',
            to: step.toAgent?.name || 'Unknown',
            reason: step.reason || 'Agent handoff'
          });
          } else if (step.type === 'tool_call') {
          // Check if it's a transfer tool (handoff)
          if (step.tool_name && step.tool_name.includes('transfer_to_')) {
            const toAgent = step.tool_name.replace('transfer_to_', '');
            sendEvent('handoff', {
              from: agentName,
              to: toAgent,
              reason: 'Agent handoff via transfer tool'
            });
          } else {
            // Send agent processing event with specific message
            const statusMessage = getAgentStatusMessage(agentName, step.tool_name);
            sendEvent('agent_processing', {
              agent: agentName,
              tool: step.tool_name,
              message: statusMessage,
              status: 'processing'
            });
            
            sendEvent('tool_call', {
              agent: agentName,
              tool: step.tool_name,
              status: 'started'
            });
            
            // Check if Task Planner is creating a task plan
            if (agentName === 'Task_Planner_Agent' && step.tool_name === 'create_task_plan') {
              sendEvent('task_plan_creating', {
                agent: 'Task_Planner_Agent',
                status: 'creating'
              });
            }
          }
          } else if (step.type === 'agent_start') {
          // Send processing event when agent starts
          const statusMessage = getAgentStatusMessage(agentName);
          sendEvent('agent_processing', {
            agent: agentName,
            message: statusMessage,
            status: 'started'
          });
          }
        },
      onStepFinish: (step) => {
        if (step.type === 'tool_call') {
          sendEvent('tool_call', {
            agent: step.agent?.name || 'Unknown',
            tool: step.tool_name,
            status: 'completed',
            result: step.result
          });
          
          // Check if Task Planner created a task plan
          if (step.agent?.name === 'Task_Planner_Agent' && step.tool_name === 'create_task_plan' && step.result) {
            const result = step.result;
            if (result.success && result.filepath) {
              // Read the markdown file and send it
              const fs = require('fs');
              const path = require('path');
              
              try {
                const markdownContent = fs.readFileSync(result.filepath, 'utf-8');
                sendEvent('task_plan_created', {
                  agent: 'Task_Planner_Agent',
                  filename: result.filename,
                  markdown: markdownContent,
                  taskCount: result.taskCount,
                  conversation_id: conversationId
                });
              } catch (err) {
                console.error('Error reading task plan markdown:', err);
              }
            }
          }
        }
      }
    });
    } catch (runError) {
      throw runError;
    }
    

    // Extract the final response
    let finalResponse = '';
    let lastAgent = 'EspressoBot_Orchestrator';
    
    // Handle the new state-based result structure
    if (result && result.state) {
      const state = result.state;
      
      // Get the current agent (with underscore prefix)
      if (state._currentAgent && state._currentAgent.name) {
        lastAgent = state._currentAgent.name;
      }
      
      // Extract from _currentStep.output (this is where the final output is)
      if (state._currentStep && state._currentStep.output) {
        finalResponse = state._currentStep.output;
        sendEvent('agent_message', {
          agent: lastAgent,
          content: finalResponse,
          timestamp: new Date().toISOString()
        });
      } else if (state._modelResponses && Array.isArray(state._modelResponses) && state._modelResponses.length > 0) {
        // Fallback: extract from modelResponses
        const lastResponse = state._modelResponses[state._modelResponses.length - 1];
        if (lastResponse.output && Array.isArray(lastResponse.output) && lastResponse.output.length > 0) {
          const output = lastResponse.output[0];
          if (output.content && Array.isArray(output.content) && output.content.length > 0) {
            const textContent = output.content.find(c => c.type === 'output_text');
            if (textContent && textContent.text) {
              finalResponse = textContent.text;
              sendEvent('agent_message', {
                agent: lastAgent,
                content: finalResponse,
                timestamp: new Date().toISOString()
              });
            }
          }
        }
      }
    } else if (result && result.finalOutput) {
      // Fallback to old structure
      finalResponse = result.finalOutput;
      sendEvent('agent_message', {
        agent: lastAgent,
        content: finalResponse,
        timestamp: new Date().toISOString()
      });
    } else if (result && typeof result === 'string') {
      // Result might be a direct string
      finalResponse = result;
      sendEvent('agent_message', {
        agent: lastAgent,
        content: finalResponse,
        timestamp: new Date().toISOString()
      });
    } else {
      // Log unexpected result structure
      console.error('Unexpected result structure - cannot extract response');
    }

    // Send task summary if tasks were created
    if (context.tasks.length > 0) {
      sendEvent('task_summary', {
        tasks: context.tasks,
        conversation_id: conv_id
      });
    }

    // Send memory summary if memories were stored
    if (context.memories.length > 0) {
      sendEvent('memory_summary', {
        memories: context.memories,
        count: context.memories.length
      });
    }

    // Save messages to database
    if (finalResponse) {
      try {
        // Save user message - extract text content from userMessage object if needed
        let userMessageContent = message; // Use the original message text
        if (typeof userMessage === 'object' && userMessage.content) {
          // If userMessage has content array (for images), extract just the text part
          if (Array.isArray(userMessage.content)) {
            const textContent = userMessage.content.find(c => c.type === 'text');
            userMessageContent = textContent ? textContent.text : message;
          } else {
            userMessageContent = userMessage.content;
          }
        }
        
        await prisma.messages.create({
          data: {
            conv_id: parseInt(conversationId),
            role: 'user',
            content: userMessageContent,
            created_at: new Date()
          }
        });
        
        // Save assistant response
        await prisma.messages.create({
          data: {
            conv_id: parseInt(conversationId),
            role: 'assistant',
            content: finalResponse,
            created_at: new Date()
          }
        });
        
        // Update conversation updated_at
        await prisma.conversations.update({
          where: { id: parseInt(conversationId) },
          data: {
            updated_at: new Date()
          }
        });
        
        console.log('Saved conversation messages');
      } catch (e) {
        console.error('Error saving conversation:', e);
      }
    }

    // Send completion event
    sendEvent('done', {
      finalResponse,
      agentsInvolved: Array.from(new Set([
        'EspressoBot_Orchestrator',
        ...Object.keys(context.results)
      ])),
      tasksCreated: context.tasks.length,
      memoriesStored: context.memories.length
    });

  } catch (error) {
    console.error('Multi-agent orchestrator error:', error);
    sendEvent('error', {
      message: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    });
  } finally {
    res.end();
  }
});

// Health check endpoint
router.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    agents: [
      'EspressoBot_Orchestrator',
      'Memory_Agent',
      'Task_Planner_Agent',
      'Product_Creation_Agent',
      'Product_Update_Agent'
    ]
  });
});

// Test endpoint
router.post('/test', async (req, res) => {
  try {
    const result = await run(espressoBotOrchestrator, 'Hello test', {
      maxTurns: 1
    });
    
    let response = 'No response';
    if (result && result.state && result.state._currentStep && result.state._currentStep.output) {
      response = result.state._currentStep.output;
    }
    
    res.json({ 
      success: true, 
      response,
      hasState: !!(result && result.state),
      hasCurrentStep: !!(result && result.state && result.state._currentStep),
      hasOutput: !!(result && result.state && result.state._currentStep && result.state._currentStep.output),
      stateKeys: result && result.state ? Object.keys(result.state) : [],
      currentTurn: result && result.state ? result.state._currentTurn : null,
      currentAgent: result && result.state && result.state._currentAgent ? result.state._currentAgent.name : null
    });
  } catch (error) {
    res.json({ 
      success: false, 
      error: error.message,
      stack: error.stack
    });
  }
});

export default router;