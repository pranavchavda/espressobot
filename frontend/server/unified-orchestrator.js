import { Router } from 'express';
import * as prismaClient from '@prisma/client';
import { run } from '@openai/agents';
import { unifiedAgent } from './basic-agent-unified.js';
import { taskGeneratorAgent, writePlanMdTool, readPlanMdTool, getTodosTool, generateTodosTool } from './task-generator-agent.js';
import { runMemoryExtraction } from './memory-agent.js';
import { findRelevantMemories, formatMemoriesForContext } from './memory-embeddings.js';

const PrismaClient = prismaClient.PrismaClient;
const prisma = new PrismaClient();
const router = Router();

// Track active agent runs for interruption
const activeAgentRuns = new Map();

// Helper to send SSE messages
function sendSse(res, eventName, data) {
  if (res.writableEnded) {
    console.warn(`Attempted to send SSE event '${eventName}' after stream ended.`);
    return;
  }
  try {
    console.log(`Sending SSE event: ${eventName}`);
    res.write(`event: ${eventName}\n`);
    res.write(`data: ${JSON.stringify(data)}\n\n`);
  } catch (e) {
    console.error(`Error writing to SSE stream (event: ${eventName}):`, e.message);
    if (!res.writableEnded) {
      res.end();
    }
  }
}

// Helper to read and send task markdown via SSE
async function sendTaskMarkdown(res, conversationId) {
  try {
    const { readFileSync, existsSync } = await import('fs');
    const { resolve, dirname } = await import('path');
    const { fileURLToPath } = await import('url');
    
    const __filename = fileURLToPath(import.meta.url);
    const __dirname = dirname(__filename);
    const plansDir = resolve(__dirname, 'plans');
    const filePath = resolve(plansDir, `TODO-${conversationId}.md`);
    
    if (existsSync(filePath)) {
      const content = readFileSync(filePath, 'utf-8');
      const tasks = [];
      
      // Parse markdown to extract task status
      const lines = content.split(/\r?\n/);
      lines.forEach((line, index) => {
        const match = line.match(/^\s*-\s*\[( |x)\]\s*(.+)$/i);
        if (match) {
          const isCompleted = match[1].toLowerCase() === 'x';
          const isInProgress = match[2].includes('🔄');
          const taskText = match[2].replace('🔄 ', '');
          
          tasks.push({
            index,
            text: taskText,
            status: isCompleted ? 'completed' : (isInProgress ? 'in_progress' : 'pending')
          });
        }
      });
      
      sendSse(res, 'task_markdown', {
        conversation_id: conversationId,
        markdown: content,
        tasks: tasks
      });
      
      console.log(`Sent task markdown for conversation ${conversationId}, ${tasks.length} tasks`);
    }
  } catch (err) {
    console.error('Error sending task markdown:', err);
  }
}

router.post('/run', async (req, res) => {
  console.log('\n========= UNIFIED ORCHESTRATOR REQUEST RECEIVED =========');
  const { message, conv_id: existing_conv_id, forceTaskGen } = req.body || {};
  let conversationId = existing_conv_id;

  // Setup SSE
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.flushHeaders();
  
  console.log('SSE headers set');

  // Track created tasks for this session
  const sessionTaskIds = new Set();
  let isStreaming = false;

  try {
    if (typeof message !== 'string' || !message.trim()) {
      sendSse(res, 'error', { message: 'Request body must include a non-empty message string' });
      return res.end();
    }
    
    console.log('Request message:', message);

    const USER_ID = 1;
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

    const MAX_HISTORY_MESSAGES = parseInt(process.env.MAX_HISTORY_MESSAGES || '10', 10);
    const recentHistory = history.slice(-MAX_HISTORY_MESSAGES);
    const historyText = recentHistory.map(m => `${m.role}: ${m.content}`).join('\n');
    const MAX_TURNS = parseInt(process.env.MAX_TURNS || '20', 20);
    console.log('Formatted conversation history with', recentHistory.length, 'messages');

    // Find relevant memories for context
    const relevantMemories = await findRelevantMemories(message, USER_ID);
    const memoryContext = formatMemoriesForContext(relevantMemories);
    
    let agentInput = message;
    if (historyText) {
      agentInput = `Previous conversation:\n${historyText}\n\nUser: ${message}`;
    }
    
    // Add memories if available
    if (memoryContext) {
      agentInput = memoryContext + '\n' + agentInput;
    }
    
    // Add conversation ID context for the agent
    agentInput += `\n\n[SYSTEM CONTEXT]\nconversation_id=${conversationId}\n`;
    
    // Add force task generation instruction if enabled
    if (forceTaskGen) {
      agentInput += `\nIMPORTANT: The user has explicitly requested that you MUST use task generation for this request. Call generate_todos immediately, regardless of task complexity.\n`;
    }
    
    agentInput += `[/SYSTEM CONTEXT]`;
    
    console.log('Agent input prepared, forceTaskGen:', forceTaskGen);
    
    // Notify client with conversation ID
    sendSse(res, 'conv_id', { conversationId });
    
    // Send initial status
    sendSse(res, 'agent_status', { status: 'analyzing' });

    // MCP polling disabled – EspressoBot will generate the plan on its first tool call.

    // Set up markdown file polling
    let pollMarkdownInterval = null;
    let lastMarkdownContent = '';
    
    // Function to poll and send markdown updates
    const pollTaskMarkdown = async () => {
      try {
        const { readFileSync, existsSync } = await import('fs');
        const { resolve, dirname } = await import('path');
        const { fileURLToPath } = await import('url');
        
        const __filename = fileURLToPath(import.meta.url);
        const __dirname = dirname(__filename);
        const plansDir = resolve(__dirname, 'plans');
        const filePath = resolve(plansDir, `TODO-${conversationId}.md`);
        
        if (existsSync(filePath)) {
          const content = readFileSync(filePath, 'utf-8');
          // Only send if content has changed
          if (content !== lastMarkdownContent) {
            lastMarkdownContent = content;
            await sendTaskMarkdown(res, conversationId);
            console.log('Sent updated task markdown via polling');
          }
        }
      } catch (err) {
        console.error('Error polling task markdown:', err);
      }
    };
    
    // Start polling every 500ms
    pollMarkdownInterval = setInterval(pollTaskMarkdown, 500);
    console.log('Started task markdown polling');

    // Run unified agent with event tracking
    console.log('Running unified agent...');
    
    // Track generate_todos calls to prevent loops
    const generateTodosCallCount = new Map();
    
    // Store this agent run for potential interruption
    const runController = {
      aborted: false,
      pollInterval: pollMarkdownInterval,
      response: res,
      conversationId: conversationId
    };
    activeAgentRuns.set(conversationId, runController);
    console.log(`Stored active agent run for conversation ${conversationId}`);
    
    const result = await run(unifiedAgent, agentInput, {
      maxTurns: MAX_TURNS,
      trace: {
        workflow_name: 'EspressoBot Workflow',
        metadata: { conversation_id: conversationId }
      },
      onStepStart: (step) => {
        console.log('*** onStepStart triggered ***');
        console.log('Step type:', step.type);
        console.log('Step:', JSON.stringify(step, null, 2).substring(0, 300));
        
        // Loop prevention for generate_todos
        if (step.type === 'tool_call' && step.tool_name === 'generate_todos') {
          const currentCount = generateTodosCallCount.get(conversationId) || 0;
          console.log(`[LOOP PREVENTION] generate_todos call #${currentCount + 1} for conversation ${conversationId}`);
          
          if (currentCount >= 2) {
            console.error(`[LOOP PREVENTION] BLOCKING: Already called ${currentCount} times!`);
            throw new Error(`Loop detected: generate_todos already called ${currentCount} times. Task generation should only happen once per conversation.`);
          }
          
          generateTodosCallCount.set(conversationId, currentCount + 1);
        }
        
        if (step.type === 'tool_call' && step.tool_name === 'create_task') {
          console.log('Task creation tool started!');
          sendSse(res, 'agent_status', { status: 'creating_task' });
        }
      },
      onStepFinish: (step) => {
        
        console.log('*** onStepFinish triggered ***');
        console.log('Step type:', step.type);
        console.log('Step tool_name:', step.tool_name);
        console.log('Step result:', JSON.stringify(step, null, 2).substring(0, 500));

        // Send appropriate updates based on the tool called
        if (step.type === 'tool_call') {
          if (step.tool_name === 'update_task_status' && step.result) {
            // For status updates, send a focused update for just this task
            try {
              const args = step.tool_args || {};
              console.log('Task status update - args:', args);
              
              if (args.task_id && args.status) {
                sendSse(res, 'task_status_update', {
                  taskId: args.task_id,
                  status: args.status,
                  conversation_id: conversationId
                });
                console.log(`Sent focused task_status_update for task ${args.task_id} -> ${args.status}`);
              }
            } catch (err) {
              console.error('Error sending task status update:', err);
            }
          } else if (['generate_todos', 'create_task', 'get_todos'].includes(step.tool_name)) {
            // For other task tools, send the full markdown
            console.log(`Task-related tool called: ${step.tool_name}, sending markdown`);
            (async () => {
              try {
                await sendTaskMarkdown(res, conversationId);
              } catch (err) {
                console.error('Error sending task markdown:', err);
              }
            })();
          }
        }
        
        if (step.type === 'tool_call' && step.tool_name === 'create_task' && step.result) {
          console.log('Task creation completed! Result:', step.result);
          
          // Immediately fetch tasks when create_task completes
          (async () => {
            try {
              const { spawn } = await import('child_process');
              const mcpProcess = spawn('npx', ['-y', '@pranavchavda/todo-mcp-server'], {
                stdio: ['pipe', 'pipe', 'pipe']
              });
              
              const request = JSON.stringify({
                jsonrpc: "2.0",
                id: 1,
                method: "tools/call",
                params: {
                  name: "list_tasks",
                  arguments: {
                    conversation_id: conversationId.toString(),
                    limit: MAX_TURNS
                  }
                }
              });
              
              mcpProcess.stdin.write(request + '\n');
              mcpProcess.stdin.end();
              
              let responseData = '';
              mcpProcess.stdout.on('data', (data) => {
                responseData += data.toString();
              });
              
              mcpProcess.on('close', () => {
                try {
                  const lines = responseData.split('\n').filter(line => line.trim());
                  const jsonLine = lines.find(line => line.startsWith('{"result"'));
                  
                  if (jsonLine) {
                    const parsed = JSON.parse(jsonLine);
                    const text = parsed.result?.content?.[0]?.text;
                    
                    if (text) {
                      const match = text.match(/(\[[\s\S]*\])/);
                      if (match) {
                        const tasksArray = JSON.parse(match[1]);
                        console.log('Real-time task fetch via onStepFinish found', tasksArray.length, 'tasks');
                        
                        const taskProgressItems = tasksArray.map(task => ({
                          id: `task-${task.id}`,
                          content: task.title || task.description || '',
                          status: task.status === 'completed' ? 'completed' : task.status === 'in_progress' ? 'in_progress' : 'pending',
                          conversation_id: conversationId,
                          toolName: 'todo_task',
                          action: task.description,
                          result: task.status === 'completed' ? 'Task completed' : undefined
                        }));
                        
                        sendSse(res, 'task_summary', { 
                          tasks: taskProgressItems,
                          total: tasksArray.length,
                          completed: tasksArray.filter(t => t.status === 'completed').length
                        });
                        
                        console.log('Sent REAL-TIME task_summary via onStepFinish with', taskProgressItems.length, 'tasks');
                      }
                    }
                  }
                } catch (err) {
                  console.error('Error in onStepFinish task fetch:', err);
                }
              });
            } catch (err) {
              console.error('Error with onStepFinish immediate task fetch:', err);
            }
          })();
        }
      },
      onMessage: (message) => {
        console.log('*** onMessage triggered ***');
        console.log('Agent message type:', typeof message);
        console.log('Agent message keys:', Object.keys(message || {}));
        console.log('Agent message:', JSON.stringify(message, null, 2).substring(0, 500));
        
        if (message.tool_calls) {
          for (const toolCall of message.tool_calls) {
            const toolName = toolCall.name;
            console.log('Tool call:', toolName, 'status:', toolCall.status);
            
            if (toolCall.status === 'running') {
              // Handle different tool types
              if (toolName === 'create_task') {
                sendSse(res, 'agent_status', { status: 'creating_task' });
              } else if (toolName === 'update_task' || toolName === 'complete_task') {
                sendSse(res, 'agent_status', { status: 'updating_task' });
              } else if (toolName.includes('search') || toolName.includes('get')) {
                sendSse(res, 'agent_status', { status: 'searching' });
              } else {
                sendSse(res, 'agent_status', { status: 'processing', tool: toolName });
              }
            }
            
            if (toolCall.status === 'complete' && toolCall.output) {
              // Track created tasks and fetch them immediately
              if (toolName === 'create_task') {
                try {
                  let taskData = toolCall.output;
                  console.log('Task created! Raw output:', taskData);
                  
                  // Extract task ID from response
                  let taskId = null;
                  if (typeof taskData === 'string') {
                    const idMatch = taskData.match(/task (\d+)/i) || taskData.match(/"id":\s*(\d+)/) || taskData.match(/ID (\d+)/i);
                    if (idMatch) {
                      taskId = parseInt(idMatch[1]);
                    }
                  }
                  
                  if (taskId) {
                    sessionTaskIds.add(taskId);
                    console.log('Created task ID:', taskId, '- fetching details immediately...');
                    
                    // Immediately fetch the created task details using direct MCP call
                    (async () => {
                      try {
                        const { spawn } = await import('child_process');
                        const mcpProcess = spawn('npx', ['-y', '@pranavchavda/todo-mcp-server'], {
                          stdio: ['pipe', 'pipe', 'pipe']
                        });
                        
                        const request = JSON.stringify({
                          jsonrpc: "2.0",
                          id: 1,
                          method: "tools/call",
                          params: {
                            name: "list_tasks",
                            arguments: {
                              conversation_id: conversationId.toString(),
                              limit: 10
                            }
                          }
                        });
                        
                        mcpProcess.stdin.write(request + '\n');
                        mcpProcess.stdin.end();
                        
                        let responseData = '';
                        mcpProcess.stdout.on('data', (data) => {
                          responseData += data.toString();
                        });
                        
                        mcpProcess.on('close', () => {
                          try {
                            const lines = responseData.split('\n').filter(line => line.trim());
                            const jsonLine = lines.find(line => line.startsWith('{"result"'));
                            
                            if (jsonLine) {
                              const parsed = JSON.parse(jsonLine);
                              const text = parsed.result?.content?.[0]?.text;
                              
                              if (text) {
                                const match = text.match(/(\[[\s\S]*\])/);
                                if (match) {
                                  const tasksArray = JSON.parse(match[1]);
                                  console.log('Real-time task fetch found', tasksArray.length, 'tasks');
                                  
                                  // Send updated task_summary with all current tasks
                                  const taskProgressItems = tasksArray.map(task => ({
                                    id: `task-${task.id}`,
                                    content: task.title || task.description || '',
                                    status: task.status === 'completed' ? 'completed' : task.status === 'in_progress' ? 'in_progress' : 'pending',
                                    conversation_id: conversationId,
                                    toolName: 'todo_task',
                                    action: task.description,
                                    result: task.status === 'completed' ? 'Task completed' : undefined
                                  }));
                                  
                                  sendSse(res, 'task_summary', { 
                                    tasks: taskProgressItems,
                                    total: tasksArray.length,
                                    completed: tasksArray.filter(t => t.status === 'completed').length
                                  });
                                  
                                  console.log('Sent real-time task_summary with', taskProgressItems.length, 'tasks');
                                }
                              }
                            }
                          } catch (err) {
                            console.error('Error parsing immediate task fetch:', err);
                          }
                        });
                      } catch (err) {
                        console.error('Error with immediate task fetch:', err);
                      }
                    })();
                  }
                } catch (e) {
                  console.error('Error parsing create_task output:', e);
                }
              }
              
              // Track task updates
              else if ((toolName === 'update_task' || toolName === 'complete_task') && toolCall.input) {
                const taskId = toolCall.input.id || toolCall.input.task_id;
                if (taskId) {
                  const newStatus = toolName === 'complete_task' ? 'completed' : (toolCall.input.status || 'in_progress');
                  sendSse(res, 'task_updated', {
                    taskId: taskId,
                    status: newStatus,
                    conversation_id: conversationId
                  });
                }
              }
            }
          }
        }
        
        // Stream text content
        if (message.content && typeof message.content === 'string') {
          if (!isStreaming) {
            isStreaming = true;
            sendSse(res, 'agent_status', { status: 'responding' });
          }
          sendSse(res, 'assistant_delta', { delta: message.content });
        }
      }
    });
    
    // Stop polling when agent completes
    if (pollMarkdownInterval) {
      clearInterval(pollMarkdownInterval);
      console.log('Stopped task markdown polling');
    }
    
    console.log('Agent run completed');
    console.log('=== AGENT RUN RESULT ===');
    console.log('Result object keys:', Object.keys(result || {}));
    console.log('Result state:', result.state ? Object.keys(result.state) : 'No state');
    console.log('Tool use tracker:', result.state?.toolUseTracker);
    console.log('Final output:', result.state?.currentStep);
    console.log('Trace ID:', result.state?.trace?.id);
    console.log('======================');
    
    // Send final task markdown after agent completes
    console.log('Sending final task markdown after agent completion');
    await sendTaskMarkdown(res, conversationId);

    // After completion, fetch tasks directly using spawn instead of agent's MCP connection
    console.log('Starting direct task fetching...');
    try {
      console.log(`Fetching tasks directly for conversation_id=${conversationId}`);
      
      // Use spawn to call the MCP server directly
      const { spawn } = await import('child_process');
      const { promisify } = await import('util');
      
      const mcpProcess = spawn('npx', ['-y', '@pranavchavda/todo-mcp-server'], {
        stdio: ['pipe', 'pipe', 'pipe']
      });
      
      const request = JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/call",
        params: {
          name: "list_tasks",
          arguments: {
            conversation_id: conversationId.toString(),
            limit: 20,
            order: "created_at",
            direction: "desc"
          }
        }
      });
      
      mcpProcess.stdin.write(request + '\n');
      mcpProcess.stdin.end();
      
      let responseData = '';
      mcpProcess.stdout.on('data', (data) => {
        responseData += data.toString();
      });
      
      await new Promise((resolve, reject) => {
        mcpProcess.on('close', (code) => {
          if (code === 0) resolve();
          else reject(new Error(`MCP process exited with code ${code}`));
        });
        mcpProcess.on('error', reject);
      });
      
      console.log('Direct MCP response:', responseData.substring(0, 500));
      
      // Parse the response
      let tasksArray = [];
      try {
        console.log('Raw MCP response lines:', responseData.split('\n').map((line, i) => `${i}: ${line.substring(0, 100)}`));
        
        const lines = responseData.split('\n').filter(line => line.trim());
        const jsonLine = lines.find(line => line.startsWith('{"result"'));
        
        if (jsonLine) {
          const parsed = JSON.parse(jsonLine);
          const text = parsed.result?.content?.[0]?.text;
          console.log('Extracted text from MCP response:', text?.substring(0, 200));
          
          if (text) {
            const match = text.match(/(\[[\s\S]*\])/);
            if (match) {
              tasksArray = JSON.parse(match[1]);
              console.log('Successfully parsed tasks from direct MCP call:', tasksArray.length, 'tasks');
              console.log('First task details:', tasksArray[0]);
            } else {
              console.log('No JSON array found in text');
            }
          } else {
            console.log('No text content found in MCP response');
          }
        } else {
          console.log('No JSON result line found in MCP response');
        }
      } catch (err) {
        console.error('Error parsing direct MCP response:', err);
        console.error('Response data:', responseData);
      }
      
      // Create task progress items
      const taskProgressItems = tasksArray.map(task => ({
        id: `task-${task.id}`,
        content: task.title || task.description || '',
        status: task.status === 'completed' ? 'completed' : task.status === 'in_progress' ? 'in_progress' : 'pending',
        conversation_id: conversationId,
        toolName: 'todo_task',
        action: task.description,
        result: task.status === 'completed' ? 'Task completed' : undefined
      }));
      
      sendSse(res, 'task_summary', { 
        tasks: taskProgressItems,
        total: tasksArray.length,
        completed: tasksArray.filter(t => t.status === 'completed').length
      });
      
      console.log('Sent task_summary with', taskProgressItems.length, 'tasks via direct MCP fetch');
      
    } catch (err) {
      console.error('Error with direct task fetching:', err);
      // Send empty task summary as fallback
      sendSse(res, 'task_summary', { tasks: [], total: 0, completed: 0 });
    }
    
    // Extract the final output
    const assistantResponse = result.finalOutput || '';
    console.log('Final response length:', assistantResponse.length);
    
    // If no streaming happened, send the final response
    if (!isStreaming && assistantResponse) {
      sendSse(res, 'assistant_delta', { delta: assistantResponse });
    }
    
    // Send completion
    sendSse(res, 'conversation_id', { conv_id: conversationId });
    sendSse(res, 'done', {});
    
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
      
      // ---- 🧠 Extract memories asynchronously ----
      (async () => {
        try {
          console.log('Starting memory extraction...');
          const allMessages = [...history, 
            { role: 'user', content: message },
            { role: 'assistant', content: assistantResponse }
          ];
          
          // Run memory extraction in parallel (fire and forget)
          runMemoryExtraction(allMessages, USER_ID, conversationId)
            .then(() => console.log('Memory extraction completed'))
            .catch(err => console.error('Memory extraction error:', err));
        } catch (err) {
          console.error('Error starting memory extraction:', err);
        }
      })();

      // ---- 🎨 Generate conversation title asynchronously ----
      try {
        if (conversation.title.startsWith('Conversation')) {
          (async () => {
            try {
              const { OpenAI } = await import('openai');
              const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
              const titlePrompt = `Generate a concise, descriptive title (max 50 characters, title case, no quotes) for this chat based on the following exchange.\nUser: ${message}\nAssistant: ${assistantResponse}`;
              const completion = await openai.chat.completions.create({
                model: 'gpt-4.1-nano',
                messages: [
                  { role: 'system', content: 'You are a helpful assistant that generates short conversation titles.' },
                  { role: 'user', content: titlePrompt }
                ],
                max_tokens: 20,
                temperature: 0.3,
              });
              const newTitle = completion.choices?.[0]?.message?.content?.trim();
              if (newTitle) {
                await prisma.conversations.update({
                  where: { id: conversationId },
                  data: { title: newTitle },
                });
                console.log('Conversation title updated to:', newTitle);
              }
            } catch (titleErr) {
              console.error('Conversation title generation error:', titleErr);
            }
          })();
        }
      } catch (outerTitleErr) {
        console.error('Async title generation scheduling failed:', outerTitleErr);
      }
    }

  } catch (error) {
    console.error('\n====== UNIFIED ORCHESTRATOR ERROR ======');
    console.error('Error:', error);
    
    if (!res.writableEnded) {
      sendSse(res, 'error', { 
        message: 'An error occurred', 
        details: error.message
      });
    }
  } finally {
    // Clean up active agent run
    activeAgentRuns.delete(conversationId);
    console.log(`Cleaned up active agent run for conversation ${conversationId}`);
    
    if (!res.writableEnded) {
      sendSse(res, 'done', {});
      res.end();
      console.log('Stream ended');
    }
    
    console.log('========= UNIFIED ORCHESTRATOR REQUEST COMPLETED =========');
  }
});

// Interrupt endpoint
router.post('/interrupt', async (req, res) => {
  console.log('\n========= INTERRUPT REQUEST RECEIVED =========');
  const { conv_id } = req.body;
  
  if (!conv_id) {
    return res.status(400).json({ 
      success: false, 
      error: 'Conversation ID is required' 
    });
  }
  
  const activeRun = activeAgentRuns.get(conv_id);
  
  if (activeRun) {
    console.log(`Found active run for conversation ${conv_id}, interrupting...`);
    
    // Set abort flag
    activeRun.aborted = true;
    
    // Clear polling interval if exists
    if (activeRun.pollInterval) {
      clearInterval(activeRun.pollInterval);
      console.log('Cleared task polling interval');
    }
    
    // Send interrupted event to SSE stream if still open
    if (activeRun.response && !activeRun.response.writableEnded) {
      sendSse(activeRun.response, 'interrupted', { 
        message: 'Agent execution was interrupted',
        conversation_id: conv_id
      });
      sendSse(activeRun.response, 'done', {});
      
      // Close the response stream
      try {
        activeRun.response.end();
        console.log('Closed SSE stream for interrupted agent');
      } catch (e) {
        console.error('Error ending response stream:', e);
      }
    }
    
    // Remove from active runs
    activeAgentRuns.delete(conv_id);
    
    res.json({ 
      success: true, 
      message: 'Agent execution interrupted',
      conversation_id: conv_id 
    });
  } else {
    console.log(`No active run found for conversation ${conv_id}`);
    res.json({ 
      success: false, 
      message: 'No active agent run found for this conversation',
      conversation_id: conv_id 
    });
  }
  
  console.log('========= INTERRUPT REQUEST COMPLETED =========');
});

export default router;