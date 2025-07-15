import { Agent, run, tool, webSearchTool,  } from '@openai/agents';
import { z } from 'zod';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { createBashAgent, bashTool, executeBashCommand } from './tools/bash-tool.js';
// MEMORY SYSTEM DISABLED - Causing infinite loops
// import { memoryAgent } from './agents/memory-agent.js';
// import { sweAgent } from './agents/swe-agent.js';
import { createConnectedSWEAgent } from './agents/swe-agent-connected.js';
import { taskPlanningAgent } from './agents/task-planning-agent.js';
import { createParallelExecutorAgent, validateParallelExecution } from './agents/parallel-executor-agent.js';
import logger from './logger.js';
import fs from 'fs/promises';
import path from 'path';
import { analyzeIntent } from './tools/intent-analyzer.js';
import { 
  addToThread, 
  getAutonomyRecommendation, 
  formatThreadForAgent 
} from './tools/conversation-thread-manager.js';
import { getSmartContext } from './context-loader/context-manager.js';
import { memoryOperations } from './memory/memory-operations-local.js';
import { viewImageTool } from './tools/view-image-tool.js';
import { parseFileTool } from './tools/file-parser-tool-safe.js';
import { saveFileTool } from './tools/file-save-tool.js';
import { fileOperationsTool } from './tools/file-operations-tool.js';
import { initializeMCPTools, callMCPTool, getMCPTools } from './tools/mcp-client.js';
import { runWithVisionRetry } from './vision-retry-wrapper.js';
import { validateAndFixBase64 } from './vision-preprocessor.js';
import { interceptConsoleForUser, restoreConsole } from './utils/console-interceptor.js';
import { toolResultCache } from './memory/tool-result-cache.js';
import { createSpawnMCPAgentTool } from './tools/spawn-mcp-agent-tool.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Store the current SSE emitter for access by spawned agents
let currentSseEmitter = null;

// Store the current abort signal for access by spawned agents
let currentAbortSignal = null;

// Create connected SWE agent instance
let connectedSWEAgent = null;
async function getSWEAgent(task = '', conversationId = null, richContext = null) {
  // Always create a new SWE agent with the provided context
  // This ensures each task gets proper context
  console.log('[Orchestrator] Creating connected SWE Agent with MCP and rich context...');
  if (currentSseEmitter) {
    currentSseEmitter('agent_processing', {
      agent: 'Orchestrator',
      message: 'Creating connected SWE Agent with MCP...',
      status: 'initializing'
    });
  }
  return await createConnectedSWEAgent(task, conversationId, richContext);
}

// Import tiered context builder
import { buildTieredContext, buildCoreContext, buildFullContext } from './context/tiered-context-builder.js';
// Import unified orchestrator prompt
import { buildUnifiedOrchestratorPrompt } from './prompts/unified-orchestrator-prompt.js';

// Task Manager Agent removed - functionality merged into Task Planning Agent

/**
 * Build rich context object for agents - now uses tiered context system
 * This is the ONLY place where RAG/memory access happens
 */
async function buildAgentContext(options) {
  const { 
    task, 
    conversationId, 
    userId, 
    userMessage, 
    autonomyLevel,
    additionalContext,
    forceFullContext = false,
    userProfile = null
  } = options;
  
  console.log(`[ORCHESTRATOR] Building tiered context for task: ${task.substring(0, 100)}...`);
  
  // Use the new tiered context builder
  const context = await buildTieredContext({
    task,
    conversationId,
    userId,
    userMessage,
    autonomyLevel,
    additionalContext,
    forceFullContext,
    userProfile,
    // Pass conversation history from the orchestrator's state
    conversationHistory: []  // Empty for now, will be populated by tiered builder
  });
  
  // Get current tasks separately (not included in tiered builder)
  if (conversationId) {
    try {
      const { getCurrentTasks } = await import('./agents/task-planning-agent.js');
      const tasksResult = await getCurrentTasks(conversationId);
      if (tasksResult.success) {
        context.currentTasks = tasksResult.tasks;
      }
    } catch (error) {
      console.log(`[ORCHESTRATOR] Error getting tasks:`, error.message);
    }
  }
  
  // Log context slice type and size
  const contextSize = JSON.stringify(context).length;
  console.log(`[ORCHESTRATOR] Built ${context.fullSlice ? 'FULL' : 'CORE'} context slice (${Math.round(contextSize / 1024)}KB)`);
  console.log(`  - Memories: ${context.relevantMemories.length}`);
  console.log(`  - Prompt Fragments: ${context.promptFragments?.length || 0}`);
  console.log(`  - Rules: ${context.relevantRules?.length || 0}`);
  console.log(`  - History: ${context.conversationHistory.length} turns`);
  
  // Debug prompt fragments
  if (context.promptFragments?.length > 0) {
    console.log(`[ORCHESTRATOR] Prompt fragments loaded:`);
    context.promptFragments.forEach((f, i) => {
      console.log(`  ${i+1}. [${f.priority}] ${f.category}: ${f.content.substring(0, 50)}...`);
    });
  }
  
  return context;
}

// analyzeBusinessLogic function moved to tiered-context-builder.js

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
    useSemanticSearch: z.boolean().describe('Enable semantic search for documentation (recommended for complex business rules or when unsure about tool usage)'),
    autonomyLevel: z.enum(['high', 'medium', 'low']).describe('Autonomy level - high: execute without confirmation, medium: confirm risky operations, low: confirm all writes'),
    // NEW: Allow orchestrator to pass curated context
    curatedContext: z.string().nullable().describe('JSON-encoded curated context that orchestrator decides to share with this agent')
  }),
  execute: async ({ agentName, task, context, useSemanticSearch = false, autonomyLevel = 'high', curatedContext }) => {
    // Use the provided autonomy level or fall back to intent analysis or default to 'high'
    const effectiveAutonomy = autonomyLevel || 
                             (global.currentIntentAnalysis?.level) || 
                             'high';
    
    console.log(`[ORCHESTRATOR] Spawning bash agent: ${agentName}`);
    console.log(`[ORCHESTRATOR] Task: ${task}`);
    console.log(`[ORCHESTRATOR] Autonomy level: ${effectiveAutonomy} (${autonomyLevel ? 'explicit' : 'from intent analysis'})`);
    console.log(`[ORCHESTRATOR] CuratedContext type: ${typeof curatedContext}, value:`, curatedContext);
    
    // Validate curatedContext
    if (curatedContext !== null && curatedContext !== undefined && typeof curatedContext !== 'string') {
      console.error(`[ORCHESTRATOR] ERROR: curatedContext must be a JSON string or null, got ${typeof curatedContext}`);
      // Convert to JSON string if it's an object/array
      if (typeof curatedContext === 'object') {
        curatedContext = JSON.stringify(curatedContext);
        console.log(`[ORCHESTRATOR] Converted curatedContext to JSON string`);
      }
    }
    
    // Send real-time progress to UI
    if (currentSseEmitter) {
      currentSseEmitter('agent_processing', {
        agent: 'EspressoBot1',
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
    const userId = global.currentUserId || null;
    
    // Use the curated context if orchestrator provided it
    let richContext;
    if (curatedContext) {
      console.log(`[ORCHESTRATOR] Using orchestrator-curated context for ${agentName}`);
      // Parse JSON-encoded context
      const parsedContext = typeof curatedContext === 'string' ? JSON.parse(curatedContext) : curatedContext;
      // Merge curated context with basic info
      richContext = {
        task,
        conversationId,
        userId,
        autonomyLevel: effectiveAutonomy,
        userProfile: global.currentUserProfile, // Include user profile
        ...(parsedContext && typeof parsedContext === 'object' && !Array.isArray(parsedContext) ? parsedContext : {})
      };
      if (parsedContext && typeof parsedContext === 'object' && !Array.isArray(parsedContext)) {
        console.log(`[ORCHESTRATOR] Curated context includes: ${Object.keys(parsedContext).join(', ')}`);
      } else {
        console.log(`[ORCHESTRATOR] Curated context type: ${typeof parsedContext}`);
      }
    } else {
      // Fallback: Build core context slice for the agent
      console.log(`[ORCHESTRATOR] No curated context provided, building core context slice`);
      richContext = await buildCoreContext({
        task,
        conversationId,
        userId,
        userMessage: task,
        autonomyLevel: effectiveAutonomy,
        conversationHistory: [], // Agent doesn't need full history
        userProfile: global.currentUserProfile // Pass user profile from global
      });
      // Add the additional context if provided
      if (context) {
        richContext.additionalContext = context;
      }
    }
    
    // Create the appropriate type of bash agent
    let bashAgent;
    if (useSemanticSearch) {
      console.log(`[ORCHESTRATOR] Using semantic bash agent with file search`);
      try {
        const { createSemanticBashAgent } = await import('./agents/semantic-bash-agent.js');
        bashAgent = await createSemanticBashAgent(agentName, task, conversationId, effectiveAutonomy, richContext);
      } catch (error) {
        console.log(`[ORCHESTRATOR] Semantic agent unavailable, falling back to regular bash agent:`, error.message);
        bashAgent = await createBashAgent(agentName, task, conversationId, effectiveAutonomy, richContext);
      }
    } else {
      bashAgent = await createBashAgent(agentName, task, conversationId, effectiveAutonomy, richContext);
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
      
      const runOptions = { maxTurns: 100, ...callbacks };
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
 * Tool to spawn a SWE (Software Engineering) agent for code generation tasks
 */
const spawnSWEAgent = tool({
  name: 'spawn_swe_agent',
  description: 'Create a SWE agent for software engineering tasks like code generation, refactoring, and API integration',
  parameters: z.object({
    task: z.string().describe('Specific software engineering task to complete'),
    context: z.string().nullable().describe('Additional context about the codebase or requirements'),
    useRichContext: z.boolean().default(true).describe('Use rich context from memory and documentation'),
  }),
  execute: async ({ task, context, useRichContext }) => {
    console.log('[ORCHESTRATOR] Spawning SWE agent for task:', task);
    
    // Send real-time progress to UI
    if (currentSseEmitter) {
      currentSseEmitter('agent_processing', {
        agent: 'EspressoBot1',
        message: 'Spawning SWE agent for code generation...',
        status: 'processing'
      });
    }
    
    try {
      // Get conversation ID and rich context
      const conversationId = global.currentConversationId;
      let richContext = null;
      
      if (useRichContext) {
        // Build rich context for the SWE agent
        richContext = await buildAgentContext({
          task: task,
          conversationId: conversationId,
          userId: global.currentUserId,
          userMessage: task,
          autonomyLevel: 'high',
          additionalContext: context,
          userProfile: global.currentUserProfile
        });
      }
      
      // Create the SWE agent with context
      const sweAgent = await getSWEAgent(task, conversationId, richContext);
      
      if (currentSseEmitter) {
        currentSseEmitter('agent_processing', {
          agent: 'SWE_Agent',
          message: 'Starting code generation...',
          status: 'processing'
        });
      }
      
      // Run the SWE agent
      const { run } = await import('@openai/agents');
      const result = await run(sweAgent, task + (context ? `\n\nContext: ${context}` : ''), {
        maxTurns: 50
      });
      
      console.log('[ORCHESTRATOR] SWE agent completed');
      
      if (currentSseEmitter) {
        currentSseEmitter('agent_processing', {
          agent: 'SWE_Agent',
          message: 'Code generation complete',
          status: 'complete'
        });
      }
      
      return {
        success: true,
        result: result.finalOutput || 'Task completed',
        agentName: 'SWE_Agent'
      };
      
    } catch (error) {
      console.error('[ORCHESTRATOR] SWE agent error:', error);
      
      if (currentSseEmitter) {
        currentSseEmitter('agent_processing', {
          agent: 'SWE_Agent',
          message: `Error: ${error.message}`,
          status: 'failed'
        });
      }
      
      return {
        success: false,
        error: error.message,
        agentName: 'SWE_Agent'
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
      autonomyLevel: z.enum(['high', 'medium', 'low']).describe('Autonomy level'),
      curatedContext: z.string().nullable().describe('JSON-encoded curated context')
    })).describe('Array of tasks to run in parallel, each with optional curated context')
  }),
  execute: async ({ tasks }) => {
    // Hot-patch to handle single task object as well as array
    const tasksArray = Array.isArray(tasks) ? tasks : [tasks];

    console.log(`[ORCHESTRATOR] Spawning ${tasksArray.length} bash agents in parallel`);
    
    // Create and run all agents in parallel
    const promises = tasksArray.map(async ({ agentName, task, context, autonomyLevel, curatedContext }) => {
      // Use the provided autonomy level or fall back to intent analysis or default to 'high'
      const effectiveAutonomy = autonomyLevel || 
                               (global.currentIntentAnalysis?.level) || 
                               'high';
      
      console.log(`[ORCHESTRATOR] Parallel agent ${agentName} using ${effectiveAutonomy} autonomy`);
      
      // Validate curatedContext
      if (curatedContext !== null && curatedContext !== undefined && typeof curatedContext !== 'string') {
        console.error(`[ORCHESTRATOR] ERROR: curatedContext must be a JSON string or null, got ${typeof curatedContext}`);
        if (typeof curatedContext === 'object') {
          curatedContext = JSON.stringify(curatedContext);
        }
      }
      
      // Get conversation ID from global context
      const conversationId = global.currentConversationId || null;
      const userId = global.currentUserId || null;
      
      // Use curated context if provided, otherwise minimal context
      let richContext;
      if (curatedContext) {
        const parsedContext = typeof curatedContext === 'string' ? JSON.parse(curatedContext) : curatedContext;
        richContext = {
          task,
          conversationId,
          userId,
          autonomyLevel: effectiveAutonomy,
          userProfile: global.currentUserProfile, // Include user profile
          ...(parsedContext && typeof parsedContext === 'object' && !Array.isArray(parsedContext) ? parsedContext : {}),
          additionalContext: context
        };
      } else {
        richContext = {
          task,
          conversationId,
          userId,
          autonomyLevel: effectiveAutonomy,
          userProfile: global.currentUserProfile, // Include user profile
          relevantMemories: [],
          relevantRules: [],
          businessLogic: {},
          currentTasks: [],
          additionalContext: context
        };
      }
      
      const bashAgent = await createBashAgent(agentName, task, conversationId, effectiveAutonomy, richContext);
      
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
        
        const runOptions = { maxTurns: 100, ...callbacks };
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
 * Tool to spawn parallel executor agents for light-bulk operations
 */
const spawnParallelExecutors = tool({
  name: 'spawn_parallel_executors',
  description: 'Spawn parallel executor agents for light-bulk operations (10-50 items). For larger operations (50+), use SWE agent instead.',
  parameters: z.object({
    items: z.array(z.string()).describe('Array of items to process (10-50 items recommended). Can be SKUs, IDs, handles, or JSON strings'),
    operation: z.string().describe('Description of the operation to perform on each item'),
    options: z.object({
      dryRun: z.boolean().describe('If true, simulate the operation without making changes'),
      throttleMs: z.number().describe('Milliseconds to wait between operations'),
      maxAgents: z.number().nullable().describe('Maximum number of parallel agents (null for auto)'),
      retryLimit: z.number().describe('Number of retries for failed items')
    }).describe('Execution options')
  }),
  execute: async ({ items, operation, options }) => {
    // Parse items if they are JSON strings
    const parsedItems = items.map(item => {
      if (typeof item === 'string' && item.startsWith('{')) {
        try {
          return JSON.parse(item);
        } catch {
          return item; // Keep as string if not valid JSON
        }
      }
      return item;
    });
    
    const itemCount = parsedItems.length;
    
    // Apply defaults
    const dryRun = options.dryRun || false;
    const throttleMs = options.throttleMs || 1000;
    const maxAgentsOption = options.maxAgents;
    const retryLimit = options.retryLimit || 2;
    
    // Check threshold
    if (itemCount > 50) {
      return {
        success: false,
        error: `Too many items (${itemCount}). For operations with 50+ items, please use SWE agent to create an optimized batch script.`,
        recommendation: 'Use SWE agent for true bulk operations'
      };
    }
    
    if (itemCount < 10) {
      return {
        success: false,
        error: `Too few items (${itemCount}). For less than 10 items, use direct MCP tools or a single bash agent.`
      };
    }
    
    // Determine optimal agent count
    const maxAgents = maxAgentsOption || Math.min(Math.ceil(itemCount / 10), 5);
    const batchSize = Math.ceil(itemCount / maxAgents);
    
    console.log(`[Orchestrator] Spawning ${maxAgents} parallel executors for ${itemCount} items (${batchSize} per agent)`);
    
    // Create batches
    const batches = [];
    for (let i = 0; i < itemCount; i += batchSize) {
      batches.push(parsedItems.slice(i, i + batchSize));
    }
    
    // Spawn executors
    const executorPromises = batches.map(async (batch, index) => {
      const instanceId = `executor-${index + 1}`;
      const executor = await createParallelExecutorAgent(instanceId, batch, operation, {
        dryRun,
        throttleMs,
        retryLimit
      });
      
      // Run the executor
      const result = await run(executor, `
[Instance: ${instanceId}]
Items to process: ${JSON.stringify(batch, null, 2)}

Operation: ${operation}

Options:
- Dry run: ${dryRun}
- Throttle: ${throttleMs}ms between operations
- Retry limit: ${retryLimit} attempts per item

Process each item according to the operation description. Use the appropriate MCP tools.
Report progress using the report_progress tool.
${dryRun ? 'This is a DRY RUN - simulate operations without making actual changes.' : ''}
      `);
      
      return {
        instanceId,
        itemCount: batch.length,
        result
      };
    });
    
    // Wait for all executors
    const results = await Promise.all(executorPromises);
    
    // Aggregate results
    const summary = {
      totalItems: itemCount,
      executorsUsed: maxAgents,
      results,
      success: results.every(r => r.result.success !== false),
      timestamp: new Date().toISOString()
    };
    
    console.log(`[Orchestrator] Parallel execution completed:`, summary);
    return summary;
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
 * Create MCP tool wrapper for orchestrator
 */
function createMCPToolWrapper(toolDef) {
  return tool({
    name: toolDef.name,
    description: toolDef.description,
    parameters: z.object(
      Object.entries(toolDef.inputSchema.properties || {}).reduce((acc, [key, schema]) => {
        // Check if field is required
        const isRequired = toolDef.inputSchema.required?.includes(key);
        
        // Convert JSON schema to Zod schema with nullable for optional fields
        let zodSchema;
        
        if (schema.type === 'string') {
          zodSchema = schema.enum ? z.enum(schema.enum) : z.string();
        } else if (schema.type === 'number') {
          zodSchema = z.number();
        } else if (schema.type === 'integer') {
          zodSchema = z.number().int();
        } else if (schema.type === 'boolean') {
          zodSchema = z.boolean();
        } else if (schema.type === 'object') {
          zodSchema = z.object({});
        } else if (schema.type === 'array') {
          // Handle array types - need proper items schema for OpenAI compatibility
          if (!schema.items) {
            console.warn(`[Orchestrator] Array schema missing items for field ${key} in tool ${toolDef.name}`);
            zodSchema = z.array(z.any());
          } else if (schema.items.type === 'string') {
            zodSchema = z.array(z.string());
          } else if (schema.items.type === 'number') {
            zodSchema = z.array(z.number());
          } else if (schema.items.type === 'integer') {
            zodSchema = z.array(z.number().int());
          } else if (schema.items.type === 'object') {
            // For object arrays, create a proper object schema recursively
            const itemSchema = {};
            if (schema.items.properties) {
              Object.entries(schema.items.properties).forEach(([itemKey, itemProp]) => {
                // Check if this property is required
                const isItemRequired = schema.items.required?.includes(itemKey);
                
                let itemZodSchema;
                if (itemProp.type === 'string') {
                  itemZodSchema = itemProp.enum ? z.enum(itemProp.enum) : z.string();
                } else if (itemProp.type === 'number') {
                  itemZodSchema = z.number();
                } else if (itemProp.type === 'integer') {
                  itemZodSchema = z.number().int();
                } else if (itemProp.type === 'boolean') {
                  itemZodSchema = z.boolean();
                } else if (itemProp.type === 'array' && itemProp.items) {
                  // Handle nested arrays
                  if (itemProp.items.type === 'object' && itemProp.items.properties) {
                    // Nested object array - recurse
                    const nestedSchema = {};
                    Object.entries(itemProp.items.properties).forEach(([nestedKey, nestedProp]) => {
                      const isNestedRequired = itemProp.items.required?.includes(nestedKey);
                      
                      if (nestedProp.type === 'string') {
                        nestedSchema[nestedKey] = nestedProp.enum ? z.enum(nestedProp.enum) : z.string();
                      } else if (nestedProp.type === 'number') {
                        nestedSchema[nestedKey] = z.number();
                      } else if (nestedProp.type === 'integer') {
                        nestedSchema[nestedKey] = z.number().int();
                      } else if (nestedProp.type === 'boolean') {
                        nestedSchema[nestedKey] = z.boolean();
                      } else {
                        nestedSchema[nestedKey] = z.any();
                      }
                      
                      // Make nested optional fields nullable
                      if (!isNestedRequired) {
                        nestedSchema[nestedKey] = nestedSchema[nestedKey].nullable().default(null);
                      }
                    });
                    itemZodSchema = z.array(z.object(nestedSchema));
                  } else if (itemProp.items.type === 'string') {
                    itemZodSchema = z.array(z.string());
                  } else {
                    itemZodSchema = z.array(z.any());
                  }
                } else if (Array.isArray(itemProp.type) && itemProp.type.includes('null')) {
                  const nonNullType = itemProp.type.find(t => t !== 'null');
                  if (nonNullType === 'string') {
                    itemZodSchema = z.string().nullable();
                  } else if (nonNullType === 'number') {
                    itemZodSchema = z.number().nullable();
                  } else {
                    itemZodSchema = z.any();
                  }
                } else {
                  itemZodSchema = z.any();
                }
                
                // Make optional item fields nullable
                if (!isItemRequired && itemZodSchema) {
                  itemZodSchema = itemZodSchema.nullable().default(null);
                }
                
                itemSchema[itemKey] = itemZodSchema;
              });
            }
            zodSchema = z.array(z.object(itemSchema));
          } else {
            zodSchema = z.array(z.any());
          }
        } else if (Array.isArray(schema.type) && schema.type.includes('null')) {
          // Handle explicitly nullable types
          const nonNullType = schema.type.find(t => t !== 'null');
          if (nonNullType === 'string') {
            zodSchema = z.string().nullable();
          } else if (nonNullType === 'number') {
            zodSchema = z.number().nullable();
          }
        }
        
        // Make optional fields nullable for OpenAI compatibility
        if (!isRequired && zodSchema) {
          // OpenAI requires .nullable() for all optional fields (not .optional())
          zodSchema = zodSchema.nullable().default(null);
        }
        
        // Add description
        if (schema.description && zodSchema) {
          zodSchema = zodSchema.describe(schema.description);
        }
        
        acc[key] = zodSchema;
        return acc;
      }, {})
    ),
    execute: async (args) => {
      console.log(`[Orchestrator] Executing MCP tool: ${toolDef.name}`);
      
      // Check if we have a conversation ID for caching
      const conversationId = global.currentConversationId;
      
      try {
        const result = await callMCPTool(toolDef.name, args);
        
        // Cache successful results for product-related tools
        if (conversationId && result && !result.error) {
          const cacheableTools = [
            'get_product', 'search_products', 'get_product_native',
            'manage_inventory_policy', 'manage_tags', 'update_pricing',
            'manage_features_metaobjects', 'manage_variant_links'
          ];
          
          if (cacheableTools.includes(toolDef.name)) {
            console.log(`[Orchestrator] Caching result for ${toolDef.name}`);
            await toolResultCache.store(
              conversationId,
              toolDef.name,
              args,
              result,
              { timestamp: new Date().toISOString() }
            );
          }
        }
        
        return result;
      } catch (error) {
        console.error(`[Orchestrator] MCP tool ${toolDef.name} failed:`, error);
        throw error;
      }
    }
  });
}

/**
 * Build orchestrator tools - now using MCP agents instead of wrapped tools
 */
async function buildOrchestratorTools() {
  const builtInSearchTool = webSearchTool();
  
  // Initialize MCP servers but don't wrap tools
  try {
    await initializeMCPTools();
    console.log('[Orchestrator] MCP servers initialized for agent delegation');
  } catch (error) {
    console.error('[Orchestrator] Failed to initialize MCP servers:', error.message);
    // Continue without MCP servers
  }
  
  // Create the spawn MCP agent tool
  const spawnMCPAgent = createSpawnMCPAgentTool();
  
  return {
    spawnMCPAgent,
    builtInSearchTool
  };
}

/**
 * Create orchestrator agent with dynamic prompt based on context
 */
function createOrchestratorAgent(contextualMessage, orchestratorContext, spawnMCPAgent, builtInSearchTool, userProfile = null) {
  // Build unified prompt based on task complexity
  const instructions = buildUnifiedOrchestratorPrompt(contextualMessage, orchestratorContext, userProfile);
  
  return new Agent({
    name: 'EspressoBot1',
    model: 'gpt-4.1',  // Back to OpenAI for now
    instructions: instructions,
  modelSettings: {
    parallelToolCalls: true
    
  },
  tools: [
    // Tool result cache search FIRST - check before calling expensive APIs
    tool({
      name: 'search_tool_cache',
      description: 'Search for cached tool results from this conversation. Use this BEFORE calling expensive tools like get_product to check if the data is already available. IMPORTANT: Include the tool name in your query for best results.',
      parameters: z.object({
        query: z.string().describe('Search query - MUST include tool name prefix for best results (e.g., "get_product ABC-123", "search_products coffee", NOT just "ABC-123")'),
        toolName: z.string().nullable().default(null).describe('Optional: specific tool name to filter by (e.g., "get_product", "search_products")'),
        limit: z.number().default(3).describe('Maximum results to return')
      }),
      execute: async ({ query, toolName, limit }) => {
        const conversationId = global.currentConversationId;
        if (!conversationId) {
          return { error: 'No conversation ID available' };
        }
        
        console.log(`[ToolCache] Searching for: "${query}" in conversation ${conversationId}`);
        
        const results = await toolResultCache.search(conversationId, query, {
          toolName,
          limit,
          similarityThreshold: 0.75
        });
        
        if (results.length === 0) {
          return { 
            found: false, 
            message: 'No cached results found. You may need to call the actual tool.' 
          };
        }
        
        return {
          found: true,
          count: results.length,
          results: results.map(r => ({
            tool: r.tool_name,
            input: r.input_params,
            output: r.output_result,
            similarity: r.similarity,
            age: `${Math.round((Date.now() - new Date(r.created_at).getTime()) / 60000)} minutes ago`
          }))
        };
      }
    }),
    tool({
      name: 'get_cache_stats',
      description: 'Get statistics about cached tool results for this conversation',
      parameters: z.object({}),
      execute: async () => {
        const conversationId = global.currentConversationId;
        if (!conversationId) {
          return { error: 'No conversation ID available' };
        }
        
        const stats = await toolResultCache.getStats(conversationId);
        return stats || { error: 'Could not retrieve cache statistics' };
      }
    }),
    spawnMCPAgent,  // New MCP agent delegation tool
    builtInSearchTool,  // Temporarily disabled - causing SDK compatibility issues
    viewImageTool,
    parseFileTool,
    saveFileTool,
    fileOperationsTool,
    tool({
      name: 'task_planner',
      description: 'Analyze requests and create structured task plans with actionable steps. Pass any context you deem relevant.',
      parameters: z.object({
        request: z.string().describe('The request to analyze, including any context you want the planner to consider')
      }),
      execute: async ({ request }) => {
        console.log('[Orchestrator] Running task planner with orchestrator-provided context');
        console.log('[Orchestrator] Request:', request.substring(0, 200) + '...');
        
        // Include conversation ID in the request
        const conversationId = global.currentConversationId;
        const enhancedRequest = request + (conversationId ? `\n\nIMPORTANT: Use conversation_id: "${conversationId}" when calling generate_todos.` : '');
        
        const result = await run(taskPlanningAgent, enhancedRequest, { maxTurns: 130 });
        
        // Emit task planning events if SSE emitter is available
        if (currentSseEmitter && global.currentConversationId) {
          try {
            const planPath = path.join(path.dirname(new URL(import.meta.url).pathname), './data/plans', `TODO-${global.currentConversationId}.md`);
            const planContent = await fs.readFile(planPath, 'utf-8');
            
            currentSseEmitter('task_plan_created', {
              markdown: planContent,
              filename: `TODO-${global.currentConversationId}.md`,
              conversation_id: global.currentConversationId
            });
            
            // Also get the parsed tasks
            const { getCurrentTasks } = await import('./agents/task-planning-agent.js');
            const tasksResult = await getCurrentTasks(global.currentConversationId);
            if (tasksResult.success && tasksResult.tasks) {
              currentSseEmitter('task_summary', {
                tasks: tasksResult.tasks.map((task, index) => ({
                  id: `task_${global.currentConversationId}_${index}`,
                  title: task.title || task.description,
                  status: task.status || 'pending',
                  index: index
                })),
                conversationId: global.currentConversationId
              });
            }
          } catch (error) {
            console.log('[Orchestrator] Could not emit task events:', error.message);
          }
        }
        
        return result.finalOutput || result;
      }
    }),
    // MEMORY SYSTEM DISABLED - Causing infinite loops
    // memoryAgent.asTool({
    //   toolName: 'memory_manager', 
    //   toolDescription: 'Store and retrieve important information from conversation memory'
    // }),
    spawnBashAgent,
    spawnSWEAgent,
    spawnParallelBashAgents,
    spawnParallelExecutors,
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
        topic_details: z.string().nullable().describe('Optional detailed description of the topic, including key context, goals, or important information')
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
  ]
});
}

// Store MCP tools globally after initialization
let spawnMCPAgentCache = null;
let builtInSearchToolCache = null;

/**
 * Initialize orchestrator tools once
 */
async function initializeOrchestratorTools() {
  if (!spawnMCPAgentCache) {
    console.log('[Orchestrator] Initializing orchestrator tools...');
    const result = await buildOrchestratorTools();
    spawnMCPAgentCache = result.spawnMCPAgent;
    builtInSearchToolCache = result.builtInSearchTool;
  }
  return { spawnMCPAgent: spawnMCPAgentCache, builtInSearchTool: builtInSearchToolCache };
}

/**
 * Run the dynamic orchestrator with a user message
 */
export async function runDynamicOrchestrator(message, options = {}) {
  const { conversationId, userId, sseEmitter, taskUpdater, abortSignal } = options;
  
  // Set global variables for SSE
  currentSseEmitter = sseEmitter;
  currentAbortSignal = abortSignal;
  
  // Intercept console logs for this user (format as user_ID to match SSE endpoint)
  interceptConsoleForUser(`user_${userId || 1}`);
  
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
  // Store user message globally for context building
  global.currentUserMessage = message;
  
  // Fetch user profile if userId is provided
  let userProfile = null;
  if (userId) {
    try {
      const { PrismaClient } = await import('@prisma/client');
      const prisma = new PrismaClient();
      userProfile = await prisma.users.findUnique({
        where: { id: userId },
        select: {
          id: true,
          email: true,
          name: true,
          bio: true,
          is_admin: true,
          created_at: true
        }
      });
      await prisma.$disconnect();
      
      if (userProfile) {
        console.log(`[Orchestrator] Loaded profile for user: ${userProfile.name || userProfile.email}`);
        // Store globally for access by spawned agents
        global.currentUserProfile = userProfile;
      }
    } catch (error) {
      console.log(`[Orchestrator] Could not load user profile:`, error.message);
    }
  }
  
  // BUILD RICH CONTEXT FIRST - Orchestrator needs this for decision making
  console.log(`[Orchestrator] Building comprehensive context for decision making...`);
  const orchestratorContext = await buildAgentContext({
    task: message,
    conversationId,
    userId,
    userMessage: message,
    autonomyLevel: intentAnalysis.level,
    additionalContext: null,
    userProfile
  });
  
  // Store orchestrator's full context globally for reference
  global.orchestratorContext = orchestratorContext;
  
  // Log what we found
  console.log(`[Orchestrator] Context analysis complete:`);
  console.log(`  - Business patterns: ${orchestratorContext.businessLogic?.patterns?.map(p => p.type).join(', ') || 'None'}`);
  console.log(`  - Memories: ${orchestratorContext.relevantMemories?.length || 0}`);
  console.log(`  - Current tasks: ${orchestratorContext.currentTasks?.length || 0}`);
  console.log(`  - Rules loaded: ${(orchestratorContext.relevantRules?.length || 0) > 0 ? 'Yes' : 'No'}`);
  
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
    // Build the orchestrator's message with its comprehensive context
    let contextualMessage = `[Conversation ID: ${conversationId}]\n\nUser: ${message}`;
    
    // Add business logic patterns if detected
    if (orchestratorContext.businessLogic?.patterns?.length > 0) {
      contextualMessage += '\n\n## Business Patterns Detected:';
      for (const pattern of orchestratorContext.businessLogic.patterns) {
        contextualMessage += `\n- ${pattern.type}`;
        if (pattern.action) contextualMessage += `: ${pattern.action}`;
        if (pattern.warning) contextualMessage += ` (WARNING: ${pattern.warning})`;
      }
    }
    
    // Add current tasks if any
    if (orchestratorContext.currentTasks?.length > 0) {
      contextualMessage += '\n\n## Current Tasks:';
      orchestratorContext.currentTasks.forEach((task, idx) => {
        const status = task.status === 'completed' ? '[x]' : 
                      task.status === 'in_progress' ? '[🔄]' : '[ ]';
        contextualMessage += `\n${idx}. ${status} ${task.title || task.description}`;
      });
    }
    
    // Add relevant memories if any
    if (orchestratorContext.relevantMemories?.length > 0) {
      contextualMessage += '\n\n## Relevant Past Experiences:';
      orchestratorContext.relevantMemories.slice(0, 3).forEach(memory => {
        contextualMessage += `\n- ${memory.content}`;
      });
    }
    
    // Add conversation topic if present
    if (orchestratorContext.conversationTopic) {
      contextualMessage += '\n\n' + orchestratorContext.conversationTopic;
    }
    
    // Add relevant prompt fragments from library
    console.log(`[Orchestrator] Checking prompt fragments: ${orchestratorContext.promptFragments?.length || 0} found`);
    if (orchestratorContext.promptFragments?.length > 0) {
      contextualMessage += '\n\n## Relevant Documentation (from Prompt Library):';
      
      // For core context, just list the fragments
      if (!orchestratorContext.fullSlice) {
        orchestratorContext.promptFragments.forEach(fragment => {
          contextualMessage += `\n\n### ${fragment.category || 'General'} (Priority: ${fragment.priority || 'medium'}):\n${fragment.content}`;
        });
      } else if (orchestratorContext.promptFragmentsByCategory) {
        // For full context, organize by category
        for (const [category, fragments] of Object.entries(orchestratorContext.promptFragmentsByCategory)) {
          contextualMessage += `\n\n### ${category.toUpperCase()}:`;
          fragments.forEach(fragment => {
            contextualMessage += `\n[${fragment.priority || 'medium'}] ${fragment.content}`;
            if (fragment.tags?.length > 0) {
              contextualMessage += ` (tags: ${fragment.tags.join(', ')})`;
            }
          });
        }
      }
    } else {
      console.log(`[Orchestrator] No prompt fragments in context - checking why...`);
      console.log(`[Orchestrator] Context keys:`, Object.keys(orchestratorContext));
    }
    
    console.log(`[Orchestrator] Prepared contextual message with rich context`);
    
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
      maxTurns: 130,
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
    
    // Initialize orchestrator tools if needed
    const { spawnMCPAgent, builtInSearchTool } = await initializeOrchestratorTools();
    
    // Create orchestrator with dynamic prompt based on context
    const orchestrator = createOrchestratorAgent(contextualMessage, orchestratorContext, spawnMCPAgent, builtInSearchTool, userProfile);
    
    // Check if we have image or file data from the API
    let messageToSend;
    let fileContextAddition = '';
    
    // Handle file data first to add context to the message
    if (global.currentFileData) {
      console.log('[DEBUG] File data found in orchestrator:', {
        type: global.currentFileData.type,
        name: global.currentFileData.name,
        size: global.currentFileData.size,
        encoding: global.currentFileData.encoding
      });
      
      // Build file context based on type
      fileContextAddition = `\n\n[Attached File: ${global.currentFileData.name} (${global.currentFileData.type})]`;
      
      if (global.currentFileData.encoding === 'text') {
        // For text files, include the content directly
        fileContextAddition += `\n\nFile content:\n\`\`\`\n${global.currentFileData.content}\n\`\`\``;
      } else {
        // For binary files, we'll need to handle them differently based on type
        fileContextAddition += `\n\nThis is a ${global.currentFileData.type} file (${(global.currentFileData.size / 1024).toFixed(1)}KB). `;
        
        // Add type-specific instructions
        switch (global.currentFileData.type) {
          case 'pdf':
            fileContextAddition += 'The PDF file has been uploaded. To extract text from this PDF:\n';
            fileContextAddition += '1. Use the `save_uploaded_file` tool to save the PDF to disk\n';
            fileContextAddition += '2. Then use bash tools to extract text:\n';
            fileContextAddition += '   - Check if pdftotext is available: `which pdftotext`\n';
            fileContextAddition += '   - If not, install poppler (package name varies by system):\n';
            fileContextAddition += '     - Ubuntu/Debian: `sudo apt-get install poppler-utils`\n';
            fileContextAddition += '     - Alpine/other: `sudo apk add poppler` or `poppler-utils`\n';
            fileContextAddition += '     - macOS: `brew install poppler`\n';
            fileContextAddition += '   - Extract text: `pdftotext saved_file.pdf -` (outputs to stdout)\n';
            fileContextAddition += '   - Or save to file: `pdftotext saved_file.pdf output.txt`';
            break;
          case 'excel':
            fileContextAddition += 'To read this Excel file, you may need to use a spreadsheet parsing tool to extract its data.';
            break;
          case 'csv':
            fileContextAddition += 'This CSV file contains structured data that can be parsed and analyzed.';
            break;
          default:
            fileContextAddition += 'The file data is available in base64 format for processing.';
        }
        
        // Store the base64 data for tool access if needed
        if (global.currentFileData.data) {
          global.currentFileBase64 = global.currentFileData.data;
        }
      }
    }
    
    // Append file context to the message
    const messageWithFileContext = contextualMessage + fileContextAddition;
    
    if (global.currentImageData) {
      console.log('[DEBUG] Image data found in orchestrator:', {
        type: global.currentImageData.type,
        hasData: !!global.currentImageData.data,
        hasUrl: !!global.currentImageData.url
      });
      
      // Use the correct format from the test files
      let imageData = global.currentImageData.type === 'data_url' 
        ? global.currentImageData.data 
        : global.currentImageData.url;
      
      // Validate and fix base64 if needed
      if (global.currentImageData.type === 'data_url') {
        imageData = validateAndFixBase64(imageData);
      }
      
      // Format message with proper multimodal structure
      messageToSend = [
        {
          role: 'user',
          content: [
            {
              type: 'input_text',
              text: messageWithFileContext
            },
            {
              type: 'input_image',
              image: imageData
            }
          ]
        }
      ];
      
      console.log('[DEBUG] Multimodal message created with proper format');
    } else {
      console.log('[DEBUG] No image data, sending text-only message');
      // For text-only messages, we can pass a string or array
      messageToSend = messageWithFileContext;
    }
    
    // Use vision retry wrapper if we have image data
    const result = global.currentImageData 
      ? await runWithVisionRetry(orchestrator, messageToSend, runOptions)
      : await run(orchestrator, messageToSend, runOptions);
    
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
    // Restore original console
    restoreConsole();
    
    // Clear the SSE emitter reference
    currentSseEmitter = null;
    global.currentSseEmitter = null;
    
    // Clear file data
    global.currentFileBase64 = null;
    global.currentConversationId = null;
    global.currentTaskUpdater = null;
    global.currentUserId = null;
    global.currentUserMessage = null;
    global.currentIntentAnalysis = null;
    global.currentUserProfile = null;
    // Clear abort signal reference
    currentAbortSignal = null;
    global.currentAbortSignal = null;
    // Clear image data
    global.currentImageData = null;
    global.currentUserImage = null;
  }
}