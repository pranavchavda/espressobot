import { Agent, run, tool, webSearchTool,  } from '@openai/agents';
import { z } from 'zod';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { createBashAgent, bashTool, executeBashCommand } from './tools/bash-tool.js';
// MEMORY SYSTEM DISABLED - Causing infinite loops
// import { memoryAgent } from './agents/memory-agent.js';
// import { sweAgent } from './agents/swe-agent.js';
import { createConnectedSWEAgent } from './agents/swe-agent-connected.js';
import { taskPlanningAgent } from './agents/task-planning-agent.js';
import ragSystemPromptManager from './memory/rag-system-prompt-manager.js';
import logger from './logger.js';
import fs from 'fs/promises';
import { analyzeIntent } from './tools/intent-analyzer.js';
import { 
  addToThread, 
  getAutonomyRecommendation, 
  formatThreadForAgent 
} from './tools/conversation-thread-manager.js';
// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Store the current SSE emitter for access by spawned agents
let currentSseEmitter = null;

// Store the current abort signal for access by spawned agents
let currentAbortSignal = null;

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
    useSemanticSearch: z.boolean().optional().default(false).describe('Enable semantic search for documentation (recommended for complex business rules or when unsure about tool usage)'),
    autonomyLevel: z.enum(['high', 'medium', 'low']).optional().default('high').describe('Autonomy level - high: execute without confirmation, medium: confirm risky operations, low: confirm all writes')
  }),
  execute: async ({ agentName, task, context, useSemanticSearch, autonomyLevel }) => {
    // Use the provided autonomy level or fall back to intent analysis or default to 'high'
    const effectiveAutonomy = autonomyLevel || 
                             (global.currentIntentAnalysis?.level) || 
                             'high';
    
    console.log(`[ORCHESTRATOR] Spawning bash agent: ${agentName}`);
    console.log(`[ORCHESTRATOR] Task: ${task}`);
    console.log(`[ORCHESTRATOR] Autonomy level: ${effectiveAutonomy} (${autonomyLevel ? 'explicit' : 'from intent analysis'})`);
    
    // Send real-time progress to UI
    if (currentSseEmitter) {
      currentSseEmitter('agent_processing', {
        agent: 'Dynamic_Bash_Orchestrator',
        message: `Spawning bash agent: ${agentName} (${effectiveAutonomy} autonomy)`,
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
        bashAgent = await createSemanticBashAgent(agentName, task, conversationId, effectiveAutonomy);
      } catch (error) {
        console.log(`[ORCHESTRATOR] Semantic agent unavailable, falling back to regular bash agent:`, error.message);
        bashAgent = await createBashAgent(agentName, task, conversationId, effectiveAutonomy);
      }
    } else {
      bashAgent = await createBashAgent(agentName, task, conversationId, effectiveAutonomy);
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
      
      // Check for abort before running
      if (currentAbortSignal?.aborted) {
        throw new Error('Agent execution was interrupted by user');
      }
      
      const runOptions = { maxTurns: 30, ...callbacks };
      if (currentAbortSignal) {
        runOptions.signal = currentAbortSignal;
      }
      
      const result = await run(bashAgent, fullPrompt, runOptions);
      
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
      // Handle abort errors specially
      if (currentAbortSignal?.aborted || error.name === 'AbortError' || error.message.includes('interrupted by user')) {
        console.log(`[ORCHESTRATOR] ${agentName} was interrupted by user`);
        if (currentSseEmitter) {
          currentSseEmitter('agent_processing', {
            agent: agentName,
            message: `Task was interrupted by user`,
            status: 'interrupted'
          });
        }
        return {
          agent: agentName,
          task: task,
          result: 'Task was interrupted by user',
          status: 'interrupted'
        };
      }
      
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
      context: z.string().nullable(),
      autonomyLevel: z.enum(['high', 'medium', 'low']).optional().default('high')
    })).describe('Array of tasks to run in parallel')
  }),
  execute: async ({ tasks }) => {
    console.log(`[ORCHESTRATOR] Spawning ${tasks.length} bash agents in parallel`);
    
    // Create and run all agents in parallel
    const promises = tasks.map(async ({ agentName, task, context, autonomyLevel }) => {
      // Use the provided autonomy level or fall back to intent analysis or default to 'high'
      const effectiveAutonomy = autonomyLevel || 
                               (global.currentIntentAnalysis?.level) || 
                               'high';
      
      console.log(`[ORCHESTRATOR] Parallel agent ${agentName} using ${effectiveAutonomy} autonomy`);
      
      // Get conversation ID from global context
      const conversationId = global.currentConversationId || null;
      const bashAgent = await createBashAgent(agentName, task, conversationId, effectiveAutonomy);
      
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
        
        // Check for abort before running
        if (currentAbortSignal?.aborted) {
          throw new Error('Agent execution was interrupted by user');
        }
        
        const runOptions = { maxTurns: 30, ...callbacks };
        if (currentAbortSignal) {
          runOptions.signal = currentAbortSignal;
        }
        
        const result = await run(bashAgent, fullPrompt, runOptions);
        
        return {
          agent: agentName,
          task: task,
          result: result,
          status: 'completed'
        };
      } catch (error) {
        // Handle abort errors specially
        if (currentAbortSignal?.aborted || error.name === 'AbortError' || error.message.includes('interrupted by user')) {
          console.log(`[ORCHESTRATOR] ${agentName} was interrupted by user`);
          return {
            agent: agentName,
            task: task,
            result: 'Task was interrupted by user',
            status: 'interrupted'
          };
        }
        
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

const builtInSearchTool = webSearchTool();
export const dynamicOrchestrator = new Agent({
  name: 'Dynamic_Bash_Orchestrator',
  model: 'o4-mini',  // Back to OpenAI for now

  instructions: `# EspressoBot Orchestrator

You orchestrate the iDrinkCoffee.com e-commerce operations by analyzing requests and delegating to specialized agents.

## CRITICAL: Autonomy-First Execution
- The system has already analyzed the user's intent and determined the appropriate autonomy level
- Access the analysis via global.currentIntentAnalysis (level: high/medium/low, reason, confidence)
- **ALWAYS pass the analyzed autonomy level to spawned agents**
- Default to 'high' autonomy unless the analysis suggests otherwise

## Execution Rules
- **High Autonomy (default)**: User provided specific values or clear commands
  - Pass autonomy='high' to agents - they will execute immediately
  - Examples: "Update SKU123 to $49.99", "Set products A,B,C to active"
- **Medium Autonomy**: High-risk operations detected
  - Pass autonomy='medium' to agents - they'll confirm only risky operations
  - Examples: Operations affecting 50+ items, bulk deletes
- **Low Autonomy**: Genuinely ambiguous requests
  - Ask for clarification before spawning agents
  - Only use when intent analysis confidence is low

## Agent Capabilities

### Bash Agents CAN:
- Execute all Python tools (run_graphql_query, update_pricing, etc.)
- Access live Shopify data and perform mutations
- Update task status
- Work autonomously based on the autonomy level you pass

### Bash Agents CANNOT:
- Access MCP (documentation, schema introspection)
- Use Context7 or Shopify Dev docs

### SWE Agent CAN:
- Create/modify tools
- Access MCP for documentation and schema
- Perform software engineering tasks

## Decision Tree
1. Check global.currentIntentAnalysis for autonomy guidance
2. For clear requests with specific values → spawn_bash_agent with autonomy from analysis
3. For high-risk operations → spawn_bash_agent with autonomy='medium'
4. For tool creation → handoff to SWE Agent
5. For documentation → handoff to SWE Agent
6. For multiple tasks → spawn_parallel_bash_agents with appropriate autonomy

## IMPORTANT: Trust the Intent Analysis
- If analysis says 'high' autonomy with specific values → DON'T second-guess
- Users are senior management - they expect immediate action on clear instructions
- Only override to 'medium' for genuinely dangerous operations (bulk deletes of 50+ items)

## Task Management
- Check tasks: get_current_tasks
- Update status: update_task_status
- Complete ALL tasks before returning control
- Mark tasks as in_progress before starting, completed when done

## Conversation Management
- Update topic: update_conversation_topic
- Use this when you identify the main goal or topic of the conversation
- Set a clear, concise topic title and optional detailed description

## Reference Files
- Business rules: /home/pranav/espressobot/frontend/server/prompts/idc-business-rules.md
- Tool guide: /home/pranav/espressobot/frontend/server/tool-docs/TOOL_USAGE_GUIDE.md`,
  tools: [
    builtInSearchTool,
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
    }),
    tool({
      name: 'update_conversation_topic',
      description: 'Update the topic title and details for the current conversation. Use this when you identify the main topic or goal of the conversation.',
      parameters: z.object({
        topic_title: z.string().describe('A concise topic title (max 200 characters) that summarizes the conversation'),
        topic_details: z.string().nullable().optional().describe('Optional detailed description of the topic, including key context, goals, or important information')
      }),
      execute: async ({ topic_title, topic_details }) => {
        try {
          const { updateConversationTopic } = await import('./tools/update-conversation-topic.js');
          
          const conversationId = global.currentConversationId;
          if (!conversationId) {
            return 'No conversation ID available';
          }
          
          const result = await updateConversationTopic({
            conversation_id: conversationId,
            topic_title,
            topic_details
          });
          
          console.log(`[Orchestrator] Updated conversation topic: ${topic_title}`);
          return result;
        } catch (error) {
          console.error(`[Orchestrator] Error updating conversation topic:`, error);
          return {
            success: false,
            error: error.message
          };
        }
      }
    })
  ],
});

/**
 * Run the dynamic orchestrator with a user message
 */
export async function runDynamicOrchestrator(message, options = {}) {
  const { conversationId, userId, sseEmitter, taskUpdater, abortSignal } = options;
  
  console.log('\n========= DYNAMIC BASH ORCHESTRATOR =========');
  console.log(`Message: ${message}`);
  console.log(`Conversation ID: ${conversationId || 'N/A'}`);
  
  // Add user message to conversation thread
  if (conversationId) {
    addToThread(conversationId, 'user', message);
  }
  
  // Analyze user intent to determine autonomy level
  const intentAnalysis = analyzeIntent(message);
  console.log(`[Orchestrator] Intent analysis: ${intentAnalysis.level} autonomy (${intentAnalysis.confidence * 100}% confidence)`);
  console.log(`[Orchestrator] Reason: ${intentAnalysis.reason}`);
  
  // Check if conversation has autonomy preference from past interactions
  const conversationAutonomy = conversationId ? getAutonomyRecommendation(conversationId) : null;
  if (conversationAutonomy) {
    console.log(`[Orchestrator] Conversation history suggests ${conversationAutonomy} autonomy preference`);
    // If user has shown preference, override intent analysis
    if (conversationAutonomy === 'high' && intentAnalysis.level !== 'high') {
      intentAnalysis.level = 'high';
      intentAnalysis.reason += ' (User prefers high autonomy based on conversation history)';
    }
  }
  
  // Store intent analysis globally for agents to access
  global.currentIntentAnalysis = intentAnalysis;
  
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
  // Set abort signal globally for spawned agents
  currentAbortSignal = abortSignal;
  global.currentAbortSignal = abortSignal;
  
  try {
    // Load smart context for the orchestrator
    let smartContext = '';
    try {
      const { getSmartContext } = await import('./context-loader/context-manager.js');
      smartContext = await getSmartContext(message, {
        includeMemory: true,
        userId: userId ? `user_${userId}` : null,
        conversationId: conversationId
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
    
    // Get conversation thread context
    let threadContext = '';
    if (conversationId) {
      threadContext = '\n\n' + formatThreadForAgent(conversationId, 5);
    }
    
    // Add conversation context and smart context if provided
    const contextualMessage = conversationId 
      ? `[Conversation ID: ${conversationId}]\n${message}${taskContext}${threadContext}${smartContext ? '\n\n' + smartContext : ''}`
      : message + (smartContext ? '\n\n' + smartContext : '');
    
    // Check if already aborted before starting
    if (abortSignal?.aborted) {
      console.log('Orchestrator execution aborted before starting');
      if (sseEmitter) {
        sseEmitter('interrupted', { message: 'Execution was interrupted by user' });
      }
      return 'Execution was interrupted by user';
    }
    
    // Run the orchestrator with callbacks for real-time streaming
    const runOptions = {
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
    };
    
    // Add abort signal to run options if provided
    if (abortSignal) {
      runOptions.signal = abortSignal;
    }
    
    const result = await run(dynamicOrchestrator, contextualMessage, runOptions);
    
    // Add assistant response to thread
    if (conversationId && result.finalOutput) {
      addToThread(conversationId, 'assistant', result.finalOutput);
    }
    
    console.log('========= ORCHESTRATOR COMPLETE =========\n');
    
    return result;
  } catch (error) {
    // Handle abort errors specially
    if (abortSignal?.aborted || error.name === 'AbortError') {
      console.log('Dynamic orchestrator execution was aborted');
      if (sseEmitter) {
        sseEmitter('interrupted', { message: 'Execution was interrupted by user' });
      }
      return 'Execution was interrupted by user';
    }
    console.error('Dynamic orchestrator error:', error);
    throw error;
  } finally {
    // Clear the SSE emitter reference
    currentSseEmitter = null;
    global.currentSseEmitter = null;
    global.currentConversationId = null;
    global.currentTaskUpdater = null;
    global.currentUserId = null;
    // Clear abort signal reference
    currentAbortSignal = null;
    global.currentAbortSignal = null;
  }
}