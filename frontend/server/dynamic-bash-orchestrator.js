import { Agent, run, tool } from '@openai/agents';
import { z } from 'zod';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { createBashAgent, bashTool, executeBashCommand } from './tools/bash-tool.js';
import { memoryAgent } from './agents/memory-agent.js';
import logger from './logger.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Store the current SSE emitter for access by spawned agents
let currentSseEmitter = null;

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
    
    // Create the bash agent
    const bashAgent = createBashAgent(agentName, task);
    
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
      const bashAgent = createBashAgent(agentName, task);
      
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
  execute: executeBashCommand
});

/**
 * Main Dynamic Orchestrator
 */
export const dynamicOrchestrator = new Agent({
  name: 'Dynamic_Bash_Orchestrator',
  instructions: `You are the main orchestrator for a dynamic bash-based system. Your role is to:
    
    1. Analyze user requests and break them into tasks
    2. Spawn specialized bash agents to complete tasks
    3. Coordinate parallel execution when possible
    4. Aggregate results and provide coherent responses
    
    You have access to:
    - Task Manager (to plan and track tasks)
    - Memory Manager (to store important information)
    - Bash Agent Spawner (to create agents for specific tasks)
    - Direct bash access (for simple commands)
    
    Best practices:
    - Use Task Manager to plan complex operations
    - Spawn specialized agents for distinct tasks (e.g., one for search, one for updates)
    - Run independent tasks in parallel
    - Use Memory Manager to store important results
    - Only use direct bash for quick checks (ls, cat, etc.)
    
    Example patterns:
    - For "update prices for products X, Y, Z" → spawn parallel agents
    - For "search then update" → spawn sequential agents
    - For "check if tool exists" → use direct bash
    
    Remember: Each bash agent has full access to Python tools and command line utilities.`,
  tools: [
    taskManagerAgent.asTool({
      toolName: 'task_manager',
      toolDescription: 'Manage and track tasks for the current operation'
    }),
    memoryAgent.asTool({
      toolName: 'memory_manager', 
      toolDescription: 'Store and retrieve important information from conversation memory'
    }),
    spawnBashAgent,
    spawnParallelBashAgents,
    orchestratorBash
  ],
  model: 'gpt-4.1'
});

/**
 * Run the dynamic orchestrator with a user message
 */
export async function runDynamicOrchestrator(message, options = {}) {
  const { conversationId, sseEmitter } = options;
  
  console.log('\n========= DYNAMIC BASH ORCHESTRATOR =========');
  console.log(`Message: ${message}`);
  console.log(`Conversation ID: ${conversationId || 'N/A'}`);
  
  let isStreaming = false;
  
  // Set the current SSE emitter for spawned agents
  currentSseEmitter = sseEmitter;
  
  try {
    // Add conversation context if provided
    const contextualMessage = conversationId 
      ? `[Conversation ID: ${conversationId}]\n${message}`
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
          sseEmitter('assistant_delta', { delta: message.content });
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
  }
}