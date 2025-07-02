import { Agent, run, tool, webSearchTool,  } from '@openai/agents';
import { z } from 'zod';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { createBashAgent, bashTool, executeBashCommand } from './tools/bash-tool.js';
// MEMORY SYSTEM DISABLED - Causing infinite loops
// import { memoryAgent } from './agents/memory-agent.js';
// import { sweAgent } from './agents/swe-agent.js';
import { createConnectedSWEAgent } from './agents/swe-agent-connected.js';
import { taskPlanningAgent } from './agents/task-planning-agent.js';
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

// Task Manager Agent removed - functionality merged into Task Planning Agent

/**
 * Tool to spawn a bash agent for a specific task
 */
const spawnBashAgent = tool({
  name: 'spawn_bash_agent',
  description: 'Create a new bash-enabled agent to complete a specific task',
  parameters: z.object({
    agentName: z.string().describe('Name for the agent (e.g., "PriceUpdater", "ProductSearcher")'),
    task: z.string().describe('Specific task for the agent to complete'),
    context: z.string().nullable().describe('Additional context or constraints'),
    useSemanticSearch: z.boolean().optional().default(false).describe('Enable semantic search for documentation (recommended for complex business rules or when unsure about tool usage)')
  }),
  execute: async ({ agentName, task, context, useSemanticSearch }) => {
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
    
    // Create the appropriate type of bash agent
    let bashAgent;
    if (useSemanticSearch) {
      console.log(`[ORCHESTRATOR] Using semantic bash agent with file search`);
      try {
        const { createSemanticBashAgent } = await import('./agents/semantic-bash-agent.js');
        bashAgent = await createSemanticBashAgent(agentName, task, conversationId);
      } catch (error) {
        console.log(`[ORCHESTRATOR] Semantic agent unavailable, falling back to regular bash agent:`, error.message);
        bashAgent = await createBashAgent(agentName, task, conversationId);
      }
    } else {
      bashAgent = await createBashAgent(agentName, task, conversationId);
    }
    
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
      
      const result = await run(bashAgent, fullPrompt, { maxTurns: 30, ...callbacks });
      
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
        
        const result = await run(bashAgent, fullPrompt, { maxTurns: 30, ...callbacks });
        
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
 * Main Dynamic Orchestrator - Using Claude Sonnet 4.0
 */
export const dynamicOrchestrator = new Agent({
  name: 'Dynamic_Bash_Orchestrator',
  model: 'o4-mini',  // Back to OpenAI for now

  instructions: `You are the main orchestrator for EspressoBot Shell Agency, helping manage the iDrinkCoffee.com e-commerce store. 

    CORE BEHAVIOR: 
    - For READ operations (searches, queries, reports): Execute immediately without asking
    - For WRITE operations (updates, creates, deletes): Confirm with user first
    - Be decisive and action-oriented while maintaining safety
    
    Your role is to:
    1. Analyze user requests and immediately execute appropriate solutions
    2. Spawn bash agents to complete tasks efficiently 
    3. Coordinate parallel execution when possible
    4. Deliver complete results, not partial samples
    5. Track and update task progress when tasks are present
    
    BUSINESS CONTEXT:
    - You're helping senior management at iDrinkCoffee.com
    - Goal: Increase sales and offer the best customer experience
    - Managing Shopify store and integrations (SkuVault, Shipstation, etc.)
    - Business rules: /home/pranav/espressobot/frontend/server/prompts/idc-business-rules.md
    - Tool guide: /home/pranav/espressobot/frontend/server/tool-docs/TOOL_USAGE_GUIDE.md
    
    You have access to:
    - Task Planner (to analyze requests and create structured task plans)
    - SWE Agent (Software Engineering Agent for creating/modifying tools AND for MCP context access)
    - Bash Agent Spawner (to create agents for specific tasks with full tool access)
    - Direct bash access (for simple commands)
    - Direct task management tools (get_current_tasks, update_task_status)
    
    IMPORTANT DISTINCTION - MCP vs API Access:
    - MCP (Model Context Protocol): Documentation, schema introspection, context retrieval
    - Shopify GraphQL API: Live data queries using run_graphql_query tool
    
    Bash agents CAN:
    - Execute ALL Python tools including run_graphql_query, run_graphql_mutation
    - Fetch live data from Shopify (products, orders, customer info, store settings)
    - Update Shopify data via GraphQL mutations
    - Run searches, pricing updates, inventory management
    - Access the CEO info via shop.accountOwner GraphQL query
    
    Bash agents CANNOT:
    - Access MCP for documentation (Context7, Shopify Dev docs)
    - Introspect GraphQL schema structure (that's MCP)
    - Search Shopify development documentation (that's MCP)
    
    Best practices:
    - EXECUTE IMMEDIATELY - don't ask permission for routine operations
    - Try available tools first, fall back to GraphQL if needed
    - For data requests: get ALL results, not samples
    - Use Task Planner only for truly complex multi-step operations
    - Spawn bash agents for ALL Shopify data operations
    - Run independent tasks in parallel
    - Use semantic search when agents need business context
    - Be decisive: if multiple approaches exist, pick one and execute
    
    Example patterns:
    - For "update product pricing" → spawn bash agent (uses update_pricing tool)
    - For "search products" → spawn bash agent (uses search_products tool)
    - For "get store/shop data" → spawn bash agent (uses run_graphql_query)
    - For "create a new tool" → handoff to SWE Agent
    - For "lookup GraphQL schema docs" → handoff to SWE Agent (MCP access)
    - For "Context7 library lookup" → handoff to SWE Agent (has MCP)
    - For "resolve library ID" → handoff to SWE Agent (has MCP)
    - For "update prices for products X, Y, Z" → spawn parallel bash agents
    - For "search then update" → spawn sequential bash agents
    - For "check if tool exists" → spawn a quick bash agent to ls the python-tools/ and tmp/ directories.
    - For "run ls in two directories" → use spawn_parallel_bash_agents
    - When user asks for "multiple agents" → always use spawn_parallel_bash_agents
    
    NEVER spawn bash agents for MCP tasks - they will fail! Handoff MCP tasks to SWE agent, and then pass the relevant information to bash agents.
    
    KEY BEHAVIORAL RULES:
    - DO NOT ask "should I proceed?" for READ operations (queries, searches, reports)
    - DO ask for confirmation before WRITE operations (updates, creates, deletes)
    - DO NOT offer partial results or samples - get complete data
    - DO NOT explain technical limitations before trying solutions
    - DO execute read requests immediately and find solutions
    - DO provide complete, actionable results
    - DO distinguish between safe reads and potentially destructive writes
    
    Task Management:
    - Use get_current_tasks to check current task list
    - Use update_task_status to mark tasks as in_progress or completed
    - Spawned bash agents can also update task status
    - Update task status as you work through them
    
   🚨 CRITICAL: When you have a task list, you MUST complete ALL tasks without stopping. This is not an asynchronous process. Always remember to ABO - Always be Orchestrating.
   - NEVER pause between tasks to report progress or wait for user confirmation
   - NEVER say "I am now ready to proceed" or "Proceeding to..." and then stop
   - NEVER hand control back to the user until ALL tasks by all the sub agents are completed
   - Have tasks 1→2→3→...→N continuously executed in a SINGLE response
   - Only return control to the user when:
     a) ALL tasks are marked "completed", OR
     b) You encounter an actual error that prevents continuation, OR
     c) You genuinely need specific information from the user
   - Remember: Users see task progress in real-time - they don't need status updates!
   - Complete the ENTIRE job, then provide the final results

    
    
    `,
  tools: [
    webSearchTool(),
    taskPlanningAgent.asTool({
      toolName: 'task_planner',
      toolDescription: 'Analyze requests and create structured task plans with actionable steps'
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
        const result = await run(sweAgent, prompt, { maxTurns: 30 });
        return result.finalOutput || result;
      }
    }),
    spawnBashAgent,
    spawnParallelBashAgents,
    // orchestratorBash,
    // Task reading and updating tools
    tool({
      name: 'get_current_tasks',
      description: 'Get the current task list for this conversation',
      parameters: z.object({}),
      execute: async () => {
        const conversationId = global.currentConversationId;
        if (!conversationId) return 'No conversation ID available';
        
        try {
          const { getCurrentTasks } = await import('./agents/task-planning-agent.js');
          const tasksResult = await getCurrentTasks(conversationId);
          if (tasksResult.success) {
            return tasksResult.tasks.map((task, index) => ({
              ...task,
              index
            }));
          } else {
            return `Error getting tasks: ${tasksResult.error}`;
          }
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
});

/**
 * Run the dynamic orchestrator with a user message
 */
export async function runDynamicOrchestrator(message, options = {}) {
  const { conversationId, userId, sseEmitter, taskUpdater } = options;
  
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
  // Set user ID globally for memory operations
  global.currentUserId = userId;
  
  try {
    // Load smart context for the orchestrator
    let smartContext = '';
    try {
      const { getSmartContext } = await import('./context-loader/context-manager.js');
      smartContext = await getSmartContext(message, {
        includeMemory: true,
        userId: userId ? `user_${userId}` : null
      });
      console.log(`[Orchestrator] Loaded smart context (${smartContext.length} chars)`);
    } catch (error) {
      console.log(`[Orchestrator] Could not load smart context:`, error.message);
    }
    
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
    
    // Add conversation context and smart context if provided
    const contextualMessage = conversationId 
      ? `[Conversation ID: ${conversationId}]\n${message}${taskContext}${smartContext ? '\n\n' + smartContext : ''}`
      : message + (smartContext ? '\n\n' + smartContext : '');
    
    // Run the orchestrator with callbacks for real-time streaming
    const result = await run(dynamicOrchestrator, contextualMessage, {
      maxTurns: 30,
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
    global.currentUserId = null;
  }
}