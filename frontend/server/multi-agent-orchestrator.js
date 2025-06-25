import express from 'express';
import { run } from '@openai/agents';
import { runWithVisionRetry } from './vision-retry-wrapper.js';
import { validateAndFixBase64 } from './vision-preprocessor.js';
import { espressoBotOrchestrator } from './agents/espressobot-orchestrator.js';
// import { simpleOrchestrator as espressoBotOrchestrator } from './agents/simple-orchestrator.js';
import EventEmitter from 'events';
import { PrismaClient } from '@prisma/client';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const router = express.Router();
const prisma = new PrismaClient();

// Event emitter for SSE
class SSEEmitter extends EventEmitter {}

// Main orchestrator endpoint
router.post('/run', async (req, res) => {
  const { conv_id, message, forceTaskGen, image } = req.body;
  
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
    if (image) {
      userMessage = {
        role: 'user',
        content: [
          { type: 'text', text: message }
        ]
      };
      
      if (image.type === 'data_url' && image.data) {
        userMessage.content.push({
          type: 'image_url',
          image_url: { url: image.data }
        });
      } else if (image.type === 'url' && image.url) {
        userMessage.content.push({
          type: 'image_url',
          image_url: { url: image.url }
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

    // Build agent input (handle both text and multimodal)
    let agentInput;
    
    // Handle image input if provided - use proper OpenAI agents SDK format
    if (image) {
      console.log('[MULTI-AGENT] Image provided:', {
        type: image.type,
        hasData: !!image.data,
        hasUrl: !!image.url,
        dataLength: image.data ? image.data.length : 0,
        urlLength: image.url ? image.url.length : 0
      });
      
      // Create content array for multimodal input
      const contentArray = [];
      
      // Add text content with conversation ID and history
      let textContent = `[Conversation ID: ${conversationId}]\n`;
      
      // Add conversation history if available
      if (messages.length > 1) {
        const historyText = messages.slice(0, -1)
          .map(m => {
            // Handle messages that might contain images
            if (typeof m.content === 'object' && Array.isArray(m.content)) {
              // Extract just the text part from multimodal messages
              const textPart = m.content.find(c => c.type === 'text' || c.type === 'input_text');
              return `${m.role === 'user' ? 'User' : 'Assistant'}: ${textPart ? (textPart.text || textPart.content) : '[Image]'}`;
            }
            return `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`;
          })
          .join('\n');
        textContent += `Previous conversation:\n${historyText}\n\nUser: ${message}`;
      } else {
        textContent += message;
      }
      
      contentArray.push({
        type: 'input_text',
        text: textContent
      });
      
      // Add image content
      if (image.type === 'data_url' && image.data) {
        // Check data URL format and size
        const dataUrlMatch = image.data.match(/^data:([^;]+);base64,(.+)$/);
        if (dataUrlMatch) {
          const mimeType = dataUrlMatch[1];
          const base64Data = dataUrlMatch[2];
          
          console.log('[MULTI-AGENT] Data URL MIME type:', mimeType);
          console.log('[MULTI-AGENT] Base64 data length:', base64Data.length);
          console.log('[MULTI-AGENT] Estimated size:', (base64Data.length * 0.75 / 1024).toFixed(2), 'KB');
          
          // Size limit checks remain the same
          const MAX_BASE64_LENGTH = 500 * 1024; // 500KB base64 (~375KB decoded)
          
          if (base64Data.length > MAX_BASE64_LENGTH) {
            console.warn('[MULTI-AGENT] ⚠️  Image too large:', (base64Data.length / 1024).toFixed(0), 'KB base64');
            sendEvent('error', {
              message: `Image is large (${(base64Data.length * 0.75 / 1024).toFixed(0)}KB). For better performance, please use images under 200KB or use an image URL instead.`,
              type: 'image_size_warning'
            });
            // Don't include the image
          } else {
            if (base64Data.length > 200 * 1024) {
              // Warn about slow processing
              sendEvent('agent_processing', {
                agent: 'System',
                message: `Processing large image (${(base64Data.length * 0.75 / 1024).toFixed(0)}KB). This may take 30-60 seconds...`,
                status: 'warning'
              });
            }
            
            // Validate and fix base64 format before adding
            const validatedDataUrl = validateAndFixBase64(image.data);
            
            // Add image using correct format
            contentArray.push({
              type: 'input_image',
              image: validatedDataUrl
            });
            console.log('[MULTI-AGENT] Added validated image to content array');
            console.log('[MULTI-AGENT] Using retry logic for base64 images to handle intermittent SDK issues');
            
            // Notify user that we're using enhanced processing
            sendEvent('status', {
              message: 'Processing screenshot with enhanced vision capabilities...',
              type: 'info'
            });
          }
        } else {
          console.error('[MULTI-AGENT] Invalid data URL format');
        }
      } else if (image.type === 'url' && image.url) {
        // URL images
        contentArray.push({
          type: 'input_image',
          image: image.url
        });
        console.log('[MULTI-AGENT] Added URL image to content array');
      }
      
      // Create proper user message format
      agentInput = [{
        role: 'user',
        content: contentArray
      }];
      
      console.log('[MULTI-AGENT] Created multimodal input with', contentArray.length, 'content items');
    } else {
      // Text-only input
      let textContent = `[Conversation ID: ${conversationId}]\n`;
      
      // Add conversation history if available
      if (messages.length > 1) {
        const historyText = messages.slice(0, -1)
          .map(m => {
            // Handle messages that might contain images
            if (typeof m.content === 'object' && Array.isArray(m.content)) {
              // Extract just the text part from multimodal messages
              const textPart = m.content.find(c => c.type === 'text' || c.type === 'input_text');
              return `${m.role === 'user' ? 'User' : 'Assistant'}: ${textPart ? (textPart.text || textPart.content) : '[Image]'}`;
            }
            return `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`;
          })
          .join('\n');
        textContent += `Previous conversation:\n${historyText}\n\nUser: ${message}`;
      } else {
        textContent += message;
      }
      
      agentInput = textContent;
    }
    
    // Set up markdown file polling like unified orchestrator does
    let pollMarkdownInterval = null;
    let lastMarkdownContent = '';
    const plansDir = path.join(__dirname, '../plans');
    
    // Function to poll for task markdown files
    const pollTaskMarkdown = () => {
      try {
        const fs = require('fs');
        const files = fs.readdirSync(plansDir);
        // Don't log every poll, too noisy
        
        // Look for markdown files for this conversation
        // Make sure conversationId is a string for comparison
        const convIdStr = String(conversationId);
        const taskFile = files.find(f => f.startsWith(`${convIdStr}_`) && f.endsWith('.md'));
        
        if (taskFile) {
          const filePath = path.join(plansDir, taskFile);
          const content = fs.readFileSync(filePath, 'utf-8');
          
          // Only send if content has changed
          if (content !== lastMarkdownContent) {
            lastMarkdownContent = content;
            sendEvent('task_plan_created', {
              agent: 'Task_Planner_Agent',
              filename: taskFile,
              markdown: content,
              taskCount: (content.match(/- \[ \]/g) || []).length,
              conversation_id: conversationId
            });
            console.log(`[MULTI-AGENT] Task markdown update sent via polling - ${taskFile} (${taskCount} tasks)`);
          }
        }
      } catch (err) {
        // Ignore errors, will try again next poll
      }
    };
    
    // Start polling every 500ms
    pollMarkdownInterval = setInterval(pollTaskMarkdown, 500);
    console.log('[MULTI-AGENT] Started task markdown polling');
    
    let result;
    try {
      // Log the input
      if (Array.isArray(agentInput)) {
        console.log('[MULTI-AGENT] Starting agent run with multimodal input');
        console.log('[MULTI-AGENT] Content items:', agentInput[0].content.length);
        agentInput[0].content.forEach((item, idx) => {
          if (item.type === 'input_text') {
            console.log(`[MULTI-AGENT] Content[${idx}]: text (${item.text.length} chars)`);
          } else if (item.type === 'input_image') {
            const isDataUrl = item.image.startsWith('data:');
            console.log(`[MULTI-AGENT] Content[${idx}]: image (${isDataUrl ? 'base64' : 'URL'})`);
          }
        });
      } else {
        console.log('[MULTI-AGENT] Starting agent run with text input length:', agentInput.length);
        console.log('[MULTI-AGENT] Input preview:', agentInput.substring(0, 200) + '...');
      }
      
      // Send initial processing event
      sendEvent('agent_processing', {
        agent: 'EspressoBot_Orchestrator',
        message: 'EspressoBot Orchestrator is analyzing your request...',
        status: 'processing'
      });
      
      // Use retry wrapper for vision requests
      const runFn = Array.isArray(agentInput) && 
        agentInput[0]?.content?.some(c => c.type === 'input_image') 
        ? runWithVisionRetry 
        : run;
      
      result = await runFn(espressoBotOrchestrator, agentInput, {
        maxTurns: 10,
        context,
        trace: {
          workflow_name: 'Multi-Agent Workflow',
          metadata: { conversation_id: conversationId }
        },
        onStepStart: (step) => {
          console.log('[MULTI-AGENT] onStepStart triggered');
          console.log('Step type:', step.type);
          console.log('Step agent:', step.agent?.name);
          console.log('Step tool:', step.tool_name);
          
          const agentName = step.agent?.name || 'Unknown';
          
          if (step.type === 'tool_call') {
            // Check if it's a transfer tool (handoff)
            if (step.tool_name && step.tool_name.includes('transfer_to_')) {
              const toAgent = step.tool_name.replace('transfer_to_', '');
              sendEvent('handoff', {
                from: agentName,
                to: toAgent,
                reason: 'Agent handoff'
              });
              
              // Send agent processing for the new agent
              const statusMessage = getAgentStatusMessage(toAgent);
              sendEvent('agent_processing', {
                agent: toAgent,
                message: statusMessage,
                status: 'processing'
              });
            } else {
              // Send tool status
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
            }
          }
        },
        onStepFinish: (step) => {
          console.log('[MULTI-AGENT] onStepFinish triggered');
          console.log('Step type:', step.type);
          console.log('Step result:', step.result ? 'has result' : 'no result');
          
          if (step.type === 'tool_call') {
            sendEvent('tool_call', {
              agent: step.agent?.name || 'Unknown',
              tool: step.tool_name,
              status: 'completed',
              result: step.result
            });
          }
        },
        onMessage: (message) => {
          console.log('[MULTI-AGENT] onMessage triggered');
          console.log('Message:', JSON.stringify(message, null, 2).substring(0, 500));
          
          // Stream partial content if available
          if (message.content) {
            sendEvent('agent_message_partial', {
              agent: 'Current',
              content: message.content,
              timestamp: new Date().toISOString()
            });
          }
        }
      });
      
    } catch (runError) {
      // Don't clear interval yet, we need it for final polling
      throw runError;
    }
    

    console.log('[MULTI-AGENT] Run completed. Result structure:', Object.keys(result || {}));
    if (result?.state) {
      console.log('[MULTI-AGENT] State keys:', Object.keys(result.state));
      console.log('[MULTI-AGENT] Current agent:', result.state._currentAgent?.name);
      console.log('[MULTI-AGENT] Steps taken:', result.state._steps?.length || 0);
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
        
        // Save message with image indicator if present
        let messageToSave = userMessageContent;
        if (image) {
          messageToSave = userMessageContent + ' [Image attached]';
        }
        
        await prisma.messages.create({
          data: {
            conv_id: parseInt(conversationId),
            role: 'user',
            content: messageToSave,
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

    // Give polling one last chance to detect any files
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Clean up polling before sending done event
    if (pollMarkdownInterval) {
      clearInterval(pollMarkdownInterval);
      console.log('[MULTI-AGENT] Stopped task markdown polling');
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
    // Clean up polling on error
    if (pollMarkdownInterval) {
      clearInterval(pollMarkdownInterval);
    }
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