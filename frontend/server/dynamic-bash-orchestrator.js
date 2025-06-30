import { Agent, run, tool } from '@openai/agents';
import { z } from 'zod';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { createBashAgent, bashTool, executeBashCommand } from './tools/bash-tool.js';
// MEMORY SYSTEM DISABLED - Causing infinite loops
// import { memoryAgent } from './agents/memory-agent.js';
// import { sweAgent } from './agents/swe-agent.js';
import { createConnectedSWEAgent } from './agents/swe-agent-connected.js';
import logger from './logger.js';
import fs from 'fs/promises';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Store the current SSE emitter for access by spawned agents
let currentSseEmitter = null;

// Create connected SWE agent instance
let connectedSWEAgent = null;
async function getSWEAgent() {
  if (!connectedSWEAgent) {
    console.log('[Orchestrator] Creating connected SWE Agent with MCP...');
    if (currentSseEmitter) {
      currentSseEmitter('agent_processing', {
        agent: 'Orchestrator',
        message: 'Creating connected SWE Agent with MCP...',
        status: 'initializing'
      });
    }
    connectedSWEAgent = await createConnectedSWEAgent();
  }
  return connectedSWEAgent;
}

/**
 * Task Manager Agent - keeps track of tasks and their status
 */
const taskManagerAgent = new Agent({
  name: 'Task_Manager',
  instructions: `You manage the task list for the current operation. You can:
    1. Break down complex requests into subtasks
    2. Track task status (pending, in_progress, completed, failed)
    3. Identify dependencies between tasks
    4. Suggest parallel execution when possible
    
    When given a request, analyze it and create a structured task list.`,
  tools: [],
  model: 'gpt-4.1-mini'
});

/**
 * Tool to spawn a bash agent for a specific task
 */
const spawnBashAgent = tool({
  name: 'spawn_bash_agent',
  description: 'Create a new bash-enabled agent to complete a specific task',
  parameters: z.object({
    agentName: z.string().describe('Name for the agent (e.g., "PriceUpdater", "ProductSearcher")'),
    task: z.string().describe('Specific task for the agent to complete'),
    context: z.string().nullable().describe('Additional context or constraints')
  }),
  execute: async ({ agentName, task, context }) => {
    console.log(`[ORCHESTRATOR] Spawning bash agent: ${agentName}`);
    console.log(`[ORCHESTRATOR] Task: ${task}`);
    
    // Send real-time progress to UI
    if (currentSseEmitter) {
      currentSseEmitter('agent_processing', {
        agent: 'Dynamic_Bash_Orchestrator',
        message: `Spawning bash agent: ${agentName}`,
        status: 'processing'
      });
      currentSseEmitter('agent_processing', {
        agent: agentName,
        message: `Task: ${task}`,
        status: 'starting'
      });
    }
    
    // Get conversation ID from global context or options
    const conversationId = global.currentConversationId || null;
    
    // Create the bash agent with conversation awareness
    const bashAgent = await createBashAgent(agentName, task, conversationId);
    
    // Run the agent with the task
    try {
      const fullPrompt = context ? `${task}\n\nContext: ${context}` : task;
      
      // Run with callbacks if SSE emitter is available
      const callbacks = currentSseEmitter ? {
        onMessage: (message) => {
          console.log(`[${agentName}] onMessage triggered`);
          if (message.content && typeof message.content === 'string') {
            currentSseEmitter('assistant_delta', { 
              delta: message.content 
            });
          }
        },
        onStepFinish: (step) => {
          console.log(`[${agentName}] Step finished:`, step.type);
          if (step.type === 'tool_call') {
            currentSseEmitter('agent_tool_call', { 
              agent: agentName,
              tool: step.tool_name,
              status: 'finished' 
            });
          }
        }
      } : {};
      
      const result = await run(bashAgent, fullPrompt, callbacks);
      
      console.log(`[ORCHESTRATOR] ${agentName} completed task`);
      
      // Send completion message to UI
      if (currentSseEmitter) {
        currentSseEmitter('agent_processing', {
          agent: agentName,
          message: `Completed task successfully`,
          status: 'completed'
        });
      }
      
      return {
        agent: agentName,
        task: task,
        result: result,
        status: 'completed'
      };
    } catch (error) {
      console.error(`[ORCHESTRATOR] ${agentName} failed:`, error);
      return {
        agent: agentName,
        task: task,
        error: error.message,
        status: 'failed'
      };
    }
  }
});

/**
 * Tool to run multiple bash agents in parallel
 */
const spawnParallelBashAgents = tool({
  name: 'spawn_parallel_bash_agents',
  description: 'Create multiple bash agents to run tasks in parallel',
  parameters: z.object({
    tasks: z.array(z.object({
      agentName: z.string(),
      task: z.string(),
      context: z.string().nullable()
    })).describe('Array of tasks to run in parallel')
  }),
  execute: async ({ tasks }) => {
    console.log(`[ORCHESTRATOR] Spawning ${tasks.length} bash agents in parallel`);
    
    // Create and run all agents in parallel
    const promises = tasks.map(async ({ agentName, task, context }) => {
      // Get conversation ID from global context
      const conversationId = global.currentConversationId || null;
      const bashAgent = await createBashAgent(agentName, task, conversationId);
      
      try {
        const fullPrompt = context ? `${task}\n\nContext: ${context}` : task;
        
        // Run with callbacks if SSE emitter is available
        const callbacks = currentSseEmitter ? {
          onMessage: (message) => {
            console.log(`[${agentName}] onMessage triggered`);
            if (message.content && typeof message.content === 'string') {
              currentSseEmitter('agent_message', { 
                agent: agentName,
                content: message.content 
              });
            }
          },
          onStepFinish: (step) => {
            console.log(`[${agentName}] Step finished:`, step.type);
            if (step.type === 'tool_call') {
              currentSseEmitter('agent_tool_call', { 
                agent: agentName,
                tool: step.tool_name,
                status: 'finished' 
              });
            }
          }
        } : {};
        
        const result = await run(bashAgent, fullPrompt, callbacks);
        
        return {
          agent: agentName,
          task: task,
          result: result,
          status: 'completed'
        };
      } catch (error) {
        return {
          agent: agentName,
          task: task,
          error: error.message,
          status: 'failed'
        };
      }
    });
    
    // Wait for all agents to complete
    const results = await Promise.all(promises);
    
    console.log(`[ORCHESTRATOR] All parallel agents completed`);
    return results;
  }
});

/**
 * Direct bash access for the orchestrator (for simple commands)
 */
const orchestratorBash = tool({
  name: 'bash',
  description: 'Execute simple bash commands directly (for quick checks, don\'t use for complex tasks)',
  parameters: bashTool.parameters,
  execute: async (params) => {
    // Pass SSE emitter if available
    return executeBashCommand(params, currentSseEmitter);
  }
});

/**
 * Main Dynamic Orchestrator
 */
export const dynamicOrchestrator = new Agent({
  name: 'Dynamic_Bash_Orchestrator',
  instructions: `You are the main orchestrator for a dynamic bash-based system. Your role is to:
    
    1. Analyze user requests and route them to the appropriate agent/tool
    2. Spawn specialized bash agents to complete tasks (but NOT for MCP tasks)
    3. Coordinate parallel execution when possible
    4. Aggregate results and provide coherent responses
    5. Track and update task progress when tasks are present
    
    CRITICAL: You CANNOT access MCP tools directly. When users ask about:
    - Context7 library resolution or documentation
    - Shopify GraphQL schema introspection
    - Shopify Dev documentation search
    - ANY MCP-related functionality
    
    You MUST use the swe_agent tool (handoff to SWE Agent) because only it has MCP access.
    
    To handoff to SWE Agent, use the swe_agent tool with the user's request as the prompt.
    
    You have access to:
    - Task Manager (to plan and track tasks)
    - SWE Agent (Software Engineering Agent for creating/modifying tools AND for MCP access)
    - Bash Agent Spawner (to create agents for specific tasks - NOTE: these do NOT have MCP access)
    - Direct bash access (for simple commands)
    
    Best practices:
    - Use Task Manager to plan complex operations
    - Handoff to SWE Agent for any tool creation or modification requests
    - Handoff to SWE Agent for ANY MCP-related tasks (Context7, Shopify Dev docs, GraphQL introspection)
    - Spawn specialized bash agents for distinct tasks (e.g., one for search, one for updates)
    - Run independent tasks in parallel
    - Only use direct bash for quick checks (ls, cat, etc.)
    
    IMPORTANT: Bash agents do NOT have MCP access. For any MCP tasks, you MUST handoff to SWE Agent.
    
    Example patterns:
    - For "create a new tool to do X" → handoff to SWE Agent
    - For "improve/fix the search tool" → handoff to SWE Agent
    - For "introspect GraphQL schema" → handoff to SWE Agent (has MCP)
    - For "search Shopify docs" → handoff to SWE Agent (has MCP)
    - For "Context7 library lookup" → handoff to SWE Agent (has MCP)
    - For "resolve library ID" → handoff to SWE Agent (has MCP)
    - For "update prices for products X, Y, Z" → spawn parallel bash agents
    - For "search then update" → spawn sequential bash agents
    - For "check if tool exists" → use direct bash
    - For "run ls in two directories" → use spawn_parallel_bash_agents
    - When user asks for "multiple agents" → always use spawn_parallel_bash_agents
    
    NEVER spawn bash agents for MCP tasks - they will fail!
    
    Remember: Each bash agent has full access to Python tools in /home/pranav/espressobot/frontend/python-tools/
    For detailed tool usage, see /home/pranav/espressobot/frontend/server/tool-docs/TOOL_USAGE_GUIDE.md
    
    Task Management:
    - If tasks are present in the conversation context, you'll see them listed
    - Use get_current_tasks to check the current task list
    - Use update_task_status to mark tasks as in_progress or completed
    - Spawned bash agents also have access to task information and can update tasks
    - Always update task status as you work through them`,
  tools: [
    taskManagerAgent.asTool({
      toolName: 'task_manager',
      toolDescription: 'Manage and track tasks for the current operation'
    }),
    // MEMORY SYSTEM DISABLED - Causing infinite loops
    // memoryAgent.asTool({
    //   toolName: 'memory_manager', 
    //   toolDescription: 'Store and retrieve important information from conversation memory'
    // }),
    tool({
      name: 'swe_agent',
      description: 'Software Engineering Agent - handoff for creating new tools, modifying existing tools, MCP access (Shopify docs, Context7), or any code-related tasks',
      parameters: z.object({
        prompt: z.string().describe('The task or request to pass to the SWE Agent')
      }),
      execute: async ({ prompt }) => {
        const sweAgent = await getSWEAgent();
        const result = await run(sweAgent, prompt);
        return result.finalOutput || result;
      }
    }),
    spawnBashAgent,
    spawnParallelBashAgents,
    orchestratorBash,
    // Task reading and updating tools
    tool({
      name: 'get_current_tasks',
      description: 'Get the current task list for this conversation',
      parameters: z.object({}),
      execute: async () => {
        const conversationId = global.currentConversationId;
        if (!conversationId) return 'No conversation ID available';
        
        try {
          const { getTodosTool } = await import('./task-generator-agent.js');
          const result = await getTodosTool.invoke(null, JSON.stringify({ conversation_id: conversationId }));
          return result;
        } catch (error) {
          return `Error getting tasks: ${error.message}`;
        }
      }
    }),
    tool({
      name: 'update_task_status',
      description: 'Update the status of a task in the current conversation',
      parameters: z.object({
        taskIndex: z.number().describe('The index of the task (0-based)'),
        status: z.enum(['pending', 'in_progress', 'completed']).describe('New status for the task')
      }),
      execute: async ({ taskIndex, status }) => {
        const conversationId = global.currentConversationId;
        if (!conversationId) return 'No conversation ID available';
        
        try {
          const { updateTaskStatus, readTasksForConversation } = await import('./utils/task-reader.js');
          const result = await updateTaskStatus(conversationId, taskIndex, status);
          
          if (result.success && currentSseEmitter) {
            // Read updated tasks and emit SSE event
            const tasksResult = await readTasksForConversation(conversationId);
            if (tasksResult.success) {
              currentSseEmitter('task_summary', {
                tasks: tasksResult.tasks.map((task, index) => ({
                  id: `task_${conversationId}_${index}`,
                  title: task.description,
                  status: task.status,
                  index: index
                })),
                conversationId: conversationId
              });
            }
          }
          
          return result.message || result;
        } catch (error) {
          return `Error updating task: ${error.message}`;
        }
      }
    })
  ],
  model: 'gpt-4.1'
});

/**
 * Run the dynamic orchestrator with a user message
 */
export async function runDynamicOrchestrator(message, options = {}) {
  const { conversationId, sseEmitter, taskUpdater } = options;
  
  console.log('\n========= DYNAMIC BASH ORCHESTRATOR =========');
  console.log(`Message: ${message}`);
  console.log(`Conversation ID: ${conversationId || 'N/A'}`);
  
  let isStreaming = false;
  
  // Set the current SSE emitter for spawned agents
  currentSseEmitter = sseEmitter;
  // Also set globally for bash tools
  global.currentSseEmitter = sseEmitter;
  // Set taskUpdater globally if provided
  global.currentTaskUpdater = taskUpdater;
  // Set conversation ID globally for bash agents
  global.currentConversationId = conversationId;
  
  try {
    // Read tasks if conversation ID is provided
    let taskContext = '';
    if (conversationId) {
      try {
        const { readTasksForConversation, formatTasksForPrompt } = await import('./utils/task-reader.js');
        const { tasks } = await readTasksForConversation(conversationId);
        if (tasks && tasks.length > 0) {
          taskContext = '\n\n' + formatTasksForPrompt(tasks);
          console.log(`[Orchestrator] Found ${tasks.length} tasks for conversation ${conversationId}`);
        }
      } catch (error) {
        console.log(`[Orchestrator] Could not read tasks:`, error.message);
      }
    }
    
    // Add conversation context if provided
    const contextualMessage = conversationId 
      ? `[Conversation ID: ${conversationId}]\n${message}${taskContext}`
      : message;
    
    // Run the orchestrator with callbacks for real-time streaming
    const result = await run(dynamicOrchestrator, contextualMessage, {
      onMessage: (message) => {
        console.log('*** Bash orchestrator onMessage ***');
        console.log('Message type:', typeof message);
        console.log('Message keys:', Object.keys(message || {}));
        console.log('Has content:', !!message?.content);
        console.log('Content type:', typeof message?.content);
        
        // Stream text content in real-time
        if (message.content && typeof message.content === 'string' && sseEmitter) {
          if (!isStreaming) {
            isStreaming = true;
            sseEmitter('agent_status', { status: 'responding' });
          }
          // Don't send deltas during streaming - let the final response handle it
          // sseEmitter('assistant_delta', { delta: message.content });
        }
        
        // Handle tool calls
        if (message.tool_calls && sseEmitter) {
          for (const toolCall of message.tool_calls) {
            console.log('Tool call:', toolCall.name);
            if (toolCall.status === 'running') {
              sseEmitter('tool_call', { 
                name: toolCall.name, 
                status: 'started' 
              });
            }
          }
        }
      },
      onStepFinish: (step) => {
        console.log('Step finished:', step.type);
        if (step.type === 'tool_call' && sseEmitter) {
          sseEmitter('tool_call', { 
            name: step.tool_name, 
            status: 'finished' 
          });
        }
      }
    });
    
    console.log('========= ORCHESTRATOR COMPLETE =========\n');
    
    return result;
  } catch (error) {
    console.error('Dynamic orchestrator error:', error);
    throw error;
  } finally {
    // Clear the SSE emitter reference
    currentSseEmitter = null;
    global.currentSseEmitter = null;
    global.currentConversationId = null;
    global.currentTaskUpdater = null;
  }
}