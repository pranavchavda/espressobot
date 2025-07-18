import { Agent, run, tool, webSearchTool, InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered } from '@openai/agents';
import { z } from 'zod';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { initializeTracing } from './config/tracing-config.js';
import { createBashAgent, bashTool, executeBashCommand } from './tools/bash-tool.js';
// MEMORY SYSTEM DISABLED - Causing infinite loops
// import { memoryAgent } from './agents/memory-agent.js';
// import { sweAgent } from './agents/swe-agent.js';
import { createConnectedSWEAgent } from './agents/swe-agent-connected.js';
import { createTaskPlan } from './agents/task-planning-agent.js';
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
// NOTE: No longer using old MCP client - using direct MCP agent access instead
import { runWithVisionRetry } from './vision-retry-wrapper.js';
import { validateAndFixBase64 } from './vision-preprocessor.js';
import { interceptConsoleForUser, restoreConsole } from './utils/console-interceptor.js';
import { feedbackLoop } from './context/feedback-loop.js';
import { toolResultCache } from './memory/tool-result-cache.js';
import { buildAgentContextPreamble, buildAgentInstructions } from './utils/agent-context-builder.js';
import { 
  createProductsAgentTool,
  createPricingAgentTool,
  createInventoryAgentTool,
  createSalesAgentTool,
  createFeaturesAgentTool,
  createMediaAgentTool,
  createIntegrationsAgentTool,
  createProductManagementAgentTool,
  createUtilityAgentTool,
  createDocumentationAgentTool, 
  createExternalMCPAgentTool,
  createSmartMCPExecuteTool,
  createPythonToolsAgentTool  // Legacy support
} from './tools/direct-mcp-agent-tools.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Initialize tracing configuration
// Previously disabled due to 5.7MB outputs causing $15+ charges
// Now controlled by environment variable with output size limits
initializeTracing('EspressoBot1');

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
  
  // Check if we have adaptive context from bulk operation
  if (bulkOperationState.isActive && 
      bulkOperationState.conversationId === conversationId && 
      bulkOperationState.adaptiveContext) {
    console.log('[ORCHESTRATOR] Using existing adaptive context from bulk operation');
    // Enhance the existing context if needed
    const { enhanceContext } = await import('./context/adaptive-context-builder.js');
    const context = await enhanceContext(bulkOperationState.adaptiveContext, [
      'recent progress',
      'failed items'
    ]);
    return context;
  }
  
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
  
  // Handle different context structures (adaptive vs traditional)
  if (context.adaptiveContext !== undefined || context.fetchedContext !== undefined) {
    // Adaptive context structure
    console.log(`[ORCHESTRATOR] Built ADAPTIVE context slice (${Math.round(contextSize / 1024)}KB)`);
    console.log(`  - Token count: ${context.tokenCount || 0}`);
    console.log(`  - Extracted data: ${context.extractedData ? 'Yes' : 'No'}`);
    console.log(`  - Fetched context keys: ${Object.keys(context.fetchedContext || {}).length}`);
    console.log(`  - Has learned patterns: ${context.learnedPatterns ? 'Yes' : 'No'}`);
  } else {
    // Traditional core/full context structure
    console.log(`[ORCHESTRATOR] Built ${context.fullSlice ? 'FULL' : 'CORE'} context slice (${Math.round(contextSize / 1024)}KB)`);
    console.log(`  - Memories: ${context.relevantMemories?.length || 0}`);
    console.log(`  - Prompt Fragments: ${context.promptFragments?.length || 0}`);
    console.log(`  - Rules: ${context.relevantRules?.length || 0}`);
    console.log(`  - History: ${context.conversationHistory?.length || 0} turns`);
  }
  
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
      
      // Run with callbacks for tool status (no token streaming for spawned agents)
      const callbacks = currentSseEmitter ? {
        onMessage: (message) => {
          console.log(`[${agentName}] onMessage triggered`);
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
        
        // Run with callbacks for tool status (no token streaming for spawned agents)
        const callbacks = currentSseEmitter ? {
          onMessage: (message) => {
            console.log(`[${agentName}] onMessage triggered`);
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
  let builtInSearchTool = null;
  
  // Try to create web search tool safely
  try {
    builtInSearchTool = webSearchTool();
    console.log('[Orchestrator] Web search tool created successfully');
  } catch (error) {
    console.error('[Orchestrator] Failed to create web search tool:', error.message);
    builtInSearchTool = null;
  }
  
  // NOTE: No longer initializing old MCP client - using direct MCP agent access instead
  // The Python Tools Agent V2 uses specialized MCP servers (1-6 tools each) for better performance
  
  // Create all specialized MCP agent tools
  const productsAgent = createProductsAgentTool();
  const pricingAgent = createPricingAgentTool();
  const inventoryAgent = createInventoryAgentTool();
  const salesAgent = createSalesAgentTool();
  const featuresAgent = createFeaturesAgentTool();
  const mediaAgent = createMediaAgentTool();
  const integrationsAgent = createIntegrationsAgentTool();
  const productManagementAgent = createProductManagementAgentTool();
  const utilityAgent = createUtilityAgentTool();
  const documentationAgent = createDocumentationAgentTool();
  const externalMCPAgent = createExternalMCPAgentTool();
  const smartMCPExecute = createSmartMCPExecuteTool();
  const pythonToolsAgent = createPythonToolsAgentTool();  // Legacy support
  
  // Validate all tools before returning
  const tools = { 
    productsAgent, pricingAgent, inventoryAgent, salesAgent, 
    featuresAgent, mediaAgent, integrationsAgent, productManagementAgent,
    utilityAgent, documentationAgent, externalMCPAgent, smartMCPExecute,
    pythonToolsAgent 
  };
  
  for (const [name, tool] of Object.entries(tools)) {
    if (!tool || typeof tool !== 'object' || !tool.name) {
      console.error(`[Orchestrator] Invalid tool detected: ${name}`, tool);
      throw new Error(`Tool ${name} is not properly defined`);
    }
  }
  
  return {
    productsAgent,
    pricingAgent,
    inventoryAgent,
    salesAgent,
    featuresAgent,
    mediaAgent,
    integrationsAgent,
    productManagementAgent,
    utilityAgent,
    documentationAgent,
    externalMCPAgent,
    smartMCPExecute,
    pythonToolsAgent,  // Legacy support
    builtInSearchTool
  };
}

/**
 * Bulk operation state tracking for guardrails with enhanced context
 */
const bulkOperationState = {
  isActive: false,
  expectedItems: 0,
  completedItems: 0,
  itemList: [],
  conversationId: null,
  retryCount: 0,
  maxRetries: 5,
  // Enhanced context fields
  taskData: null,           // Structured task data from task-data-extractor
  checkpoints: [],          // Progress checkpoints
  adaptiveContext: null,    // Adaptive context built for this operation
  lastCheckpointIndex: -1   // Track last saved checkpoint
};

/**
 * LLM-powered input chokidar to detect bulk operations intelligently
 */
const bulkOperationInputChokidar = new Agent({
  name: 'Bulk Operation Chokidar',
  model: 'gpt-4.1-mini',
  instructions: `You are an intelligent chokidar (guard) agent in the EspressoBot agency - an AI-powered assistant system that supports iDrinkCoffee.com with all manner of e-commerce tasks including product management, pricing updates, inventory control, and business operations.

Your specific role is to detect bulk operations vs simple questions.

BULK OPERATIONS to detect:
- Commands to process multiple items (fix all SKUs, update pricing for products, create batch)
- Continuation of ongoing work ("continue", "proceed with bulk task")
- Autonomous work declarations ("work silently", "no interruption")
- Explicit bulk language ("this is a bulk task", "bulk operation")

NOT BULK OPERATIONS:
- Questions about items ("are there priced SKUs?", "how many products?")  
- Single item requests ("fix this SKU", "check one product")
- Informational queries ("what is the price?", "tell me about...")
- Creating 2-3 specific named items ("create Lemo and Mixer collections")
- Research or documentation tasks ("how to create collections")
- GraphQL query requests (not mutations)

Analyze the input and determine if this is a bulk operation that needs guardrail tracking.`,
  outputType: z.object({
    isBulkOperation: z.boolean(),
    expectedItems: z.number().default(0).describe('Estimated number of items to process (0 if unclear)'),
    reasoning: z.string(),
    operationType: z.string().nullable().default(null).describe('Type of operation: create, update, fix, etc.')
  }),
});

const bulkOperationInputGuardrail = {
  name: 'bulk_operation_detector',
  execute: async ({ input, context }) => {
    console.log('[Chokidar] Input chokidar analyzing for bulk operations...');
    
    try {
      const inputText = typeof input === 'string' ? input : JSON.stringify(input);
      const result = await run(bulkOperationInputChokidar, inputText, { context });
      const analysis = result.finalOutput;
      
      console.log(`[Chokidar] Analysis: ${analysis.isBulkOperation ? 'BULK' : 'STANDARD'} - ${analysis.reasoning}`);
      
      if (analysis.isBulkOperation) {
        console.log('[Chokidar] 🎯 BULK OPERATION DETECTED BY INTELLIGENT CHOKIDAR');
        
        // Set up bulk operation tracking
        bulkOperationState.isActive = true;
        bulkOperationState.expectedItems = analysis.expectedItems || 0;
        bulkOperationState.completedItems = 0;
        bulkOperationState.conversationId = global.currentConversationId;
        bulkOperationState.operationType = analysis.operationType;
        
        // Trigger Task Planning Agent and extract task data
        console.log('[Chokidar] Triggering Task Planning Agent and data extraction for bulk operation');
        try {
          // Extract structured data from the task
          const { extractTaskData } = await import('./agents/task-data-extractor-nano.js');
          const extraction = await extractTaskData(inputText);
          
          if (extraction.success) {
            bulkOperationState.taskData = extraction.data;
            console.log(`[Chokidar] Extracted task data: ${extraction.data.entities.length} entities, action: ${extraction.data.action}`);
          }
          
          // Create task plan
          const { createTaskPlan, getTaskData } = await import('./agents/task-planning-agent.js');
          const taskPlanResult = await createTaskPlan(inputText, global.currentConversationId);
          
          if (taskPlanResult.success && taskPlanResult.tasks.length > 0) {
            console.log(`[Chokidar] Task plan created with ${taskPlanResult.tasks.length} tasks`);
            bulkOperationState.itemList = taskPlanResult.tasks;
            bulkOperationState.expectedItems = taskPlanResult.tasks.length;
            
            // Load any saved task data
            const savedTaskData = await getTaskData(global.currentConversationId);
            if (savedTaskData) {
              bulkOperationState.taskData = savedTaskData;
            }
          }
          
          // Build adaptive context for the bulk operation
          const { buildAdaptiveContext } = await import('./context/adaptive-context-builder.js');
          bulkOperationState.adaptiveContext = await buildAdaptiveContext({
            task: inputText,
            conversationId: global.currentConversationId,
            userId: global.currentUserId,
            userMessage: inputText,
            includeExtractedData: true
          });
          
          // Load any existing checkpoints
          const { loadLatestCheckpoint } = await import('./agents/progress-tracker-nano.js');
          const checkpoint = await loadLatestCheckpoint(global.currentConversationId);
          if (checkpoint) {
            bulkOperationState.completedItems = checkpoint.stats?.completed || 0;
            bulkOperationState.checkpoints = [checkpoint];
            console.log(`[Chokidar] Loaded checkpoint: ${bulkOperationState.completedItems} items already completed`);
          }
        } catch (taskPlanError) {
          console.error('[Chokidar] Failed to enhance bulk operation context:', taskPlanError.message);
        }
        
        return {
          outputInfo: `Bulk operation detected: ${analysis.reasoning}. Expected items: ${bulkOperationState.expectedItems}`,
          tripwireTriggered: false // Don't block input - just track the bulk operation
        };
      }
      
      return {
        outputInfo: `Standard operation: ${analysis.reasoning}`,
        tripwireTriggered: false
      };
      
    } catch (error) {
      console.log('[Chokidar] Input chokidar failed, falling back to simple detection:', error.message);
      
      // Fallback to simple keyword detection if LLM fails
      const inputText = typeof input === 'string' ? input : JSON.stringify(input);
      const isBulk = inputText.toLowerCase().includes('bulk') || inputText.toLowerCase().includes('continue');
      
      if (isBulk) {
        bulkOperationState.isActive = true;
        bulkOperationState.expectedItems = 0;
        bulkOperationState.completedItems = 0;
        bulkOperationState.conversationId = global.currentConversationId;
      }
      
      return {
        outputInfo: isBulk ? 'Bulk operation (fallback detection)' : 'Standard operation (fallback)',
        tripwireTriggered: false
      };
    }
  }
};

/**
 * Create output chokidar with current context
 */
function createBulkOperationOutputChokidar(conversationId = null) {
  const contextPreamble = buildAgentContextPreamble({
    agentRole: 'output completion guard',
    conversationId
  });
  
  return new Agent({
    name: 'Output Completion Chokidar',
    model: 'gpt-4.1-mini',
    instructions: `${contextPreamble}

You are an intelligent chokidar (guard) that detects "announce and stop" patterns during bulk operations while allowing genuine blockers and completions.

BULK OPERATION CONTEXT: The agent is supposed to be working on multiple items (${bulkOperationState.expectedItems || 'several'} items expected).

ANNOUNCE AND STOP PATTERNS (BLOCK THESE):
- Promises to work autonomously but returns control ("working silently", "you'll hear from me", then stops)
- Asking for permission mid-bulk when it could proceed ("would you like me to proceed?", "shall I continue?")
- Providing options instead of working ("next steps:", "how would you like to proceed?")
- Status updates without actual work ("processing...", "working on it..." without tool calls)
- Premature stopping when more work remains without a good reason
- SHOWING GRAPHQL MUTATIONS instead of executing them ("here's the mutation", "you can use this")
- Providing instructions or code samples when execution was requested

LEGITIMATE PATTERNS (ALLOW THESE):
- Actually calling tools (python_tools_agent, documentation_agent, external_mcp_agent, smart_mcp_execute)
- Genuine completion with results ("✅ All 12 items updated successfully")
- Progress reports WITH tool calls (showing actual work done)
- TRUE BLOCKERS requiring user input:
  * API rate limits with specific errors ("429 Too Many Requests", "Rate limit exceeded")
  * Authentication failures needing credentials
  * Missing required data the agent cannot determine
  * Genuine ambiguity requiring clarification
  * Partial completion with valid reason for stopping
- Questions about handling errors or exceptions that occurred
- Completion summaries asking about next steps AFTER finishing all work

DECISION CRITERIA:
1. If work is 80%+ complete AND there's a genuine blocker (rate limit, auth error, etc.) - ALLOW
2. If the agent has done substantial work and hit a real technical barrier - ALLOW
3. If asking for permission without trying first or very early in the process - BLOCK
4. If the question is about post-completion actions (all work done) - ALLOW
5. If reporting partial success with specific errors that need user decision - ALLOW
6. If the task is NOT actually a bulk operation (single item, research task, query) - ALLOW
7. If agent executed mutations and is reporting results - ALLOW
8. If agent hit a SPECIFIC error (not generic "something went wrong") - ALLOW
9. If showing GraphQL/code WITHOUT execution when user asked for action - BLOCK

Consider: 
- Has the agent made a good faith effort? 
- Is there a legitimate technical or business reason to stop?
- Did the user ask for execution or just information?
- Is this truly a bulk operation or a single task?`,
    outputType: z.object({
      isAnnounceAndStop: z.boolean(),
      hasActualWork: z.boolean(),
      isComplete: z.boolean(),
      reasoning: z.string(),
      progressCount: z.number().default(0).describe('Number of items actually processed (if detectable)')
    }),
  });
}

const bulkOperationOutputGuardrail = {
  name: 'bulk_completion_validator',
  execute: async ({ agentOutput, context }) => {
    console.log('[Chokidar] Output chokidar validating bulk operation completion...');
    
    if (!bulkOperationState.isActive) {
      console.log('[Chokidar] Not in bulk mode - allowing normal response');
      return {
        outputInfo: 'Not in bulk operation mode',
        tripwireTriggered: false
      };
    }
    
    try {
      const outputText = typeof agentOutput === 'string' ? agentOutput : JSON.stringify(agentOutput);
      
      // Update the chokidar's instructions with current state
      const contextualPrompt = `${outputText}

CURRENT BULK STATE:
- Expected items: ${bulkOperationState.expectedItems}
- Completed items: ${bulkOperationState.completedItems}
- Operation type: ${bulkOperationState.operationType || 'unknown'}

Analyze this agent output and determine if it's legitimate work or "announce and stop" behavior.`;
      
      const bulkOperationOutputChokidar = createBulkOperationOutputChokidar(bulkOperationState.conversationId);
      const result = await run(bulkOperationOutputChokidar, contextualPrompt, { context });
      const analysis = result.finalOutput;
      
      console.log(`[Chokidar] Analysis: ${analysis.isAnnounceAndStop ? 'ANNOUNCE & STOP' : 'LEGITIMATE'} - ${analysis.reasoning}`);
      
      // Update progress tracking and save checkpoint
      if (analysis.progressCount > 0) {
        bulkOperationState.completedItems += analysis.progressCount;
        console.log(`[Chokidar] Progress updated: ${bulkOperationState.completedItems}/${bulkOperationState.expectedItems} items`);
        
        // Extract and save checkpoint
        try {
          const { extractProgress, saveCheckpoint } = await import('./agents/progress-tracker-nano.js');
          const progress = await extractProgress(outputText, bulkOperationState.itemList);
          
          if (progress.success) {
            const checkpointData = {
              ...progress.progress,
              bulkOperation: {
                type: bulkOperationState.operationType,
                totalExpected: bulkOperationState.expectedItems,
                adaptiveContext: bulkOperationState.adaptiveContext ? {
                  tokenCount: bulkOperationState.adaptiveContext.tokenCount,
                  hasExtractedData: !!bulkOperationState.adaptiveContext.extractedData
                } : null
              }
            };
            
            const saved = await saveCheckpoint(bulkOperationState.conversationId, checkpointData);
            if (saved.success) {
              bulkOperationState.lastCheckpointIndex = saved.checkpointIndex;
              console.log(`[Chokidar] Saved checkpoint ${saved.checkpointIndex}`);
            }
          }
        } catch (checkpointError) {
          console.error('[Chokidar] Failed to save checkpoint:', checkpointError.message);
        }
      }
      
      // Check for completion
      if (analysis.isComplete) {
        console.log('[Chokidar] 🎉 Bulk operation marked complete by intelligent chokidar');
        // Reset all state
        bulkOperationState.isActive = false;
        bulkOperationState.retryCount = 0;
        bulkOperationState.completedItems = 0;
        bulkOperationState.expectedItems = 0;
        return {
          outputInfo: `Bulk operation complete: ${analysis.reasoning}`,
          tripwireTriggered: false
        };
      }
      
      // Block announce and stop patterns (but allow human override)
      if (analysis.isAnnounceAndStop && !analysis.hasActualWork) {
        console.log('[Chokidar] 🚫 DETECTED ANNOUNCE AND STOP PATTERN');
        
        // Store context for approval tool
        bulkOperationState.pendingGuardrailDecision = {
          pattern: 'announce_and_stop',
          reasoning: analysis.reasoning,
          completedItems: bulkOperationState.completedItems,
          expectedItems: bulkOperationState.expectedItems
        };
        
        return {
          outputInfo: `Detected announce and stop pattern: ${analysis.reasoning}`,
          tripwireTriggered: true,  // Back to automatic enforcement
          requiresApproval: true  // Keep for future use
        };
      }
      
      // Allow legitimate work
      return {
        outputInfo: `Legitimate bulk progress: ${analysis.reasoning}`,
        tripwireTriggered: false
      };
      
    } catch (error) {
      console.log('[Chokidar] Output chokidar failed, falling back to simple patterns:', error.message);
      
      // Fallback to simple pattern detection
      const outputText = typeof agentOutput === 'string' ? agentOutput : JSON.stringify(agentOutput);
      const lowerOutput = outputText.toLowerCase();
      
      const prematurePatterns = ['autonomous', 'silently', 'you\'ll hear from me', 'working on it'];
      const hasToolCalls = outputText.includes('python_tools_agent') || outputText.includes('documentation_agent') || outputText.includes('external_mcp_agent') || outputText.includes('smart_mcp_execute') || outputText.includes('completed');
      const seemsPremature = prematurePatterns.some(pattern => lowerOutput.includes(pattern));
      
      if (seemsPremature && !hasToolCalls) {
        return {
          outputInfo: 'Blocking premature return (fallback detection)',
          tripwireTriggered: true
        };
      }
      
      return {
        outputInfo: 'Allowing output (fallback detection)',
        tripwireTriggered: false
      };
    }
  }
};

/**
 * Create orchestrator agent with dynamic prompt based on context
 */
function createOrchestratorAgent(contextualMessage, orchestratorContext, mcpTools, builtInSearchTool, guardrailApprovalTool, userProfile = null) {
  // Build unified prompt based on task complexity
  const instructions = buildUnifiedOrchestratorPrompt(contextualMessage, orchestratorContext, userProfile);
  
  // Validate MCP tools before adding to agent
  const mcpToolsArray = [];
  if (mcpTools) {
    for (const [name, tool] of Object.entries(mcpTools)) {
      if (tool && typeof tool === 'object' && tool.name) {
        mcpToolsArray.push(tool);
        console.log(`[Orchestrator] Added MCP tool: ${tool.name}`);
      } else {
        console.warn(`[Orchestrator] Skipping invalid MCP tool: ${name}`, tool);
      }
    }
  }
  
  return new Agent({
    name: 'EspressoBot1',
    model: 'gpt-4.1',  // Back to gpt-4.1 until o3 organization verification is complete
    instructions: instructions,
    
    // Guardrails to enforce bulk operation behavior
    inputGuardrails: [bulkOperationInputGuardrail],
    outputGuardrails: [bulkOperationOutputGuardrail],

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
    ...mcpToolsArray,  // Add validated MCP tools
    // builtInSearchTool,  // Temporarily disabled - causing SDK compatibility issues
    ...(builtInSearchTool ? [builtInSearchTool] : []),  // Only add if it exists
    guardrailApprovalTool,  // Human-in-the-loop guardrail control
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
        
        // Import and create the task planning agent
        const { createTaskPlanningAgent } = await import('./agents/task-planning-agent.js');
        const { run } = await import('@openai/agents');
        const taskPlanningAgent = await createTaskPlanningAgent(conversationId);
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
  const { conversationId, userId, sseEmitter, taskUpdater, abortSignal, contextOverride = null } = options;
  
  // Declare operationId at function scope so it's available in catch blocks
  let operationId;
  let feedbackLoop;
  
  // Set global variables for SSE
  currentSseEmitter = sseEmitter;
  currentAbortSignal = abortSignal;
  
  // Reset bulk operation state for new conversations to prevent state leakage
  if (!bulkOperationState.conversationId || bulkOperationState.conversationId !== conversationId) {
    console.log('[Guardrail] Resetting bulk operation state for new conversation');
    bulkOperationState.isActive = false;
    bulkOperationState.retryCount = 0;
    bulkOperationState.completedItems = 0;
    bulkOperationState.expectedItems = 0;
    bulkOperationState.conversationId = conversationId;
  }
  
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
  const orchestratorContext = contextOverride || await buildAgentContext({
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
    
    // Store the base message globally for guardrail retries
    global.currentBaseMessage = message;
    global.currentOriginalContextualMessage = null; // Will be set after building full context
    
    // CONTEXT SIZE MONITORING - Add logging and limits to prevent API failures
    const MAX_CONTEXT_SIZE = 150000; // 150KB limit to prevent context explosion
    let currentSize = contextualMessage.length;
    
    function checkContextSize(section, content) {
      const sectionSize = content.length;
      if (currentSize + sectionSize > MAX_CONTEXT_SIZE) {
        console.log(`[CONTEXT WARNING] Skipping ${section} - would exceed limit (current: ${currentSize}, adding: ${sectionSize})`);
        return false;
      }
      currentSize += sectionSize;
      return true;
    }
    
    // Add business logic patterns if detected
    if (orchestratorContext.businessLogic?.patterns?.length > 0) {
      const patternsContent = '\n\n## Business Patterns Detected:' + 
        orchestratorContext.businessLogic.patterns.map(pattern => {
          let line = `\n- ${pattern.type}`;
          if (pattern.action) line += `: ${pattern.action}`;
          if (pattern.warning) line += ` (WARNING: ${pattern.warning})`;
          return line;
        }).join('');
      
      if (checkContextSize('business patterns', patternsContent)) {
        contextualMessage += patternsContent;
      }
    }
    
    // Add current tasks if any
    if (orchestratorContext.currentTasks?.length > 0) {
      const tasksContent = '\n\n## Current Tasks:' + 
        orchestratorContext.currentTasks.map((task, idx) => {
          const status = task.status === 'completed' ? '[x]' : 
                        task.status === 'in_progress' ? '[🔄]' : '[ ]';
          return `\n${idx}. ${status} ${task.title || task.description}`;
        }).join('');
      
      if (checkContextSize('current tasks', tasksContent)) {
        contextualMessage += tasksContent;
      }
    }
    
    // Add relevant memories if any (limit to top 3 to prevent size explosion)
    if (orchestratorContext.relevantMemories?.length > 0) {
      const memoriesContent = '\n\n## Relevant Past Experiences:' + 
        orchestratorContext.relevantMemories.slice(0, 3).map(memory => 
          `\n- ${memory.content.substring(0, 500)}` + (memory.content.length > 500 ? '...' : '')
        ).join('');
      
      if (checkContextSize('memories', memoriesContent)) {
        contextualMessage += memoriesContent;
      }
    }
    
    // Add conversation topic if present
    if (orchestratorContext.conversationTopic) {
      const topicContent = '\n\n' + orchestratorContext.conversationTopic.substring(0, 2000) + 
        (orchestratorContext.conversationTopic.length > 2000 ? '\n[Topic truncated for size]' : '');
      
      if (checkContextSize('conversation topic', topicContent)) {
        contextualMessage += topicContent;
      }
    }
    
    // Add relevant prompt fragments from library with size limits
    console.log(`[Orchestrator] Checking prompt fragments: ${orchestratorContext.promptFragments?.length || 0} found`);
    if (orchestratorContext.promptFragments?.length > 0) {
      let fragmentsContent = '\n\n## Relevant Documentation (from Prompt Library):';
      
      // For core context, just list the fragments with size limits
      if (!orchestratorContext.fullSlice) {
        for (const fragment of orchestratorContext.promptFragments) {
          const fragmentText = `\n\n### ${fragment.category || 'General'} (Priority: ${fragment.priority || 'medium'}):\n${fragment.content.substring(0, 1000)}` + 
            (fragment.content.length > 1000 ? '\n[Fragment truncated for size]' : '');
          
          if (currentSize + fragmentsContent.length + fragmentText.length > MAX_CONTEXT_SIZE) {
            fragmentsContent += '\n\n[Additional prompt fragments truncated to prevent context explosion]';
            break;
          }
          fragmentsContent += fragmentText;
        }
      } else if (orchestratorContext.promptFragmentsByCategory) {
        // For full context, organize by category with limits
        let categoriesProcessed = 0;
        for (const [category, fragments] of Object.entries(orchestratorContext.promptFragmentsByCategory)) {
          if (categoriesProcessed >= 5) { // Limit categories
            fragmentsContent += '\n\n[Additional categories truncated to prevent context explosion]';
            break;
          }
          
          const categoryContent = `\n\n### ${category.toUpperCase()}:` + 
            fragments.slice(0, 3).map(fragment => { // Limit fragments per category
              let line = `\n[${fragment.priority || 'medium'}] ${fragment.content.substring(0, 800)}`;
              if (fragment.content.length > 800) line += '[...]';
              if (fragment.tags?.length > 0) {
                line += ` (tags: ${fragment.tags.slice(0, 3).join(', ')})`;
              }
              return line;
            }).join('');
          
          if (currentSize + fragmentsContent.length + categoryContent.length > MAX_CONTEXT_SIZE) {
            fragmentsContent += '\n\n[Remaining categories truncated to prevent context explosion]';
            break;
          }
          fragmentsContent += categoryContent;
          categoriesProcessed++;
        }
      }
      
      if (checkContextSize('prompt fragments', fragmentsContent)) {
        contextualMessage += fragmentsContent;
      }
    } else {
      console.log(`[Orchestrator] No prompt fragments in context - checking why...`);
      console.log(`[Orchestrator] Context keys:`, Object.keys(orchestratorContext));
    }
    
    // Final size check and logging
    console.log(`[CONTEXT SIZE] Final contextual message: ${contextualMessage.length} characters (${(contextualMessage.length/1024).toFixed(1)}KB)`);
    if (contextualMessage.length > MAX_CONTEXT_SIZE) {
      console.log(`[CONTEXT ERROR] Message exceeds limit! Truncating to prevent API failure...`);
      contextualMessage = contextualMessage.substring(0, MAX_CONTEXT_SIZE) + '\n\n[Context truncated to prevent API limits - this indicates a system issue that needs investigation]';
    }
    
    console.log(`[Orchestrator] Prepared contextual message with rich context`);
    
    // Store the full contextual message globally for guardrail retries
    global.currentOriginalContextualMessage = contextualMessage;
    
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
      maxTurns: 500, // Higher limit to handle bulk operations properly
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
          // For now, send the full content - we'll implement token streaming later
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
    };
    
    // Add abort signal to run options if provided
    if (abortSignal) {
      runOptions.signal = abortSignal;
    }
    
    // Initialize orchestrator tools if needed
    const { 
      productsAgent, pricingAgent, inventoryAgent, salesAgent,
      featuresAgent, mediaAgent, integrationsAgent, productManagementAgent,
      utilityAgent, documentationAgent, externalMCPAgent, smartMCPExecute,
      pythonToolsAgent, builtInSearchTool 
    } = await buildOrchestratorTools();
    
    // Import guardrail approval tool
    const { createGuardrailApprovalTool, handleGuardrailApproval } = await import('./tools/guardrail-approval-tool.js');
    
    // Create guardrail approval tool instance
    const guardrailApprovalTool = createGuardrailApprovalTool(bulkOperationState, sseEmitter);
    
    // Create orchestrator with dynamic prompt based on context
    const mcpAgentTools = {
      productsAgent, pricingAgent, inventoryAgent, salesAgent,
      featuresAgent, mediaAgent, integrationsAgent, productManagementAgent,
      utilityAgent, documentationAgent, externalMCPAgent, smartMCPExecute,
      pythonToolsAgent  // Legacy support
    };
    const orchestrator = createOrchestratorAgent(contextualMessage, orchestratorContext, mcpAgentTools, null, guardrailApprovalTool, userProfile);
    
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
    
    // Import feedback loop for tracking
    ({ feedbackLoop } = await import('./context/feedback-loop.js'));
    operationId = `${conversationId}-${Date.now()}`;
    
    // Start tracking this operation
    feedbackLoop.startOperation(operationId, message, orchestratorContext);
    
    // Use streaming for better user experience
    let result;
    let fullResponse = ''; // Declare at proper scope for guardrail access
    
    try {
      if (global.currentImageData) {
        result = await runWithVisionRetry(orchestrator, messageToSend, runOptions);
        // For vision requests, extract the response from the result
        if (result && result.finalOutput) {
          fullResponse = result.finalOutput;
        } else if (result && result.state && result.state._currentStep && result.state._currentStep.output) {
          fullResponse = result.state._currentStep.output;
        }
        console.log('*** Vision response captured:', fullResponse ? fullResponse.substring(0, 100) + '...' : 'No response');
      } else {
        // Implement token-level streaming
        result = await run(orchestrator, messageToSend, { 
          ...runOptions, 
          stream: true 
        });
        
        // Get the text stream for token-level streaming
        const textStream = result.toTextStream();
        
        // Process the stream token by token
        try {
          for await (const chunk of textStream) {
            console.log('*** Stream token received:', chunk);
            
            if (sseEmitter) {
              if (!isStreaming) {
                isStreaming = true;
                sseEmitter('agent_status', { status: 'responding' });
              }
              // Send each token as it's generated
              sseEmitter('assistant_delta', { delta: chunk });
              fullResponse += chunk;
            }
          }
        } catch (streamError) {
          console.log('[Orchestrator] Streaming interrupted, likely by guardrail:', streamError.message);
          console.log('[Orchestrator] Accumulated fullResponse length:', fullResponse.length);
          // Don't re-throw, let the main error handling deal with guardrail exceptions
        }
        
        // Wait for completion (this might throw guardrail exceptions)
        await result.completed;
        
        console.log('*** Full streamed response:', fullResponse);
      }
      
      // Check for interruptions (human-in-the-loop)
      if (result && result.interruptions && result.interruptions.length > 0) {
        console.log('[Orchestrator] Interruption detected - approval needed');
        
        // Handle the approval flow
        const approvalResult = await handleGuardrailApproval(result, orchestratorContext, sseEmitter);
        
        if (approvalResult.needsApproval) {
          if (approvalResult.approved) {
            console.log('[Orchestrator] User approved guardrail enforcement');
            // Force bulk operation mode
            bulkOperationState.isActive = true;
            // Re-run with enforcement
            result = await run(orchestrator, { state: approvalResult.state }, runOptions);
          } else {
            console.log('[Orchestrator] User rejected guardrail enforcement');
            // Continue with original response
          }
        }
      }
    } catch (executionError) {
      // Re-throw to be handled by the main catch block
      throw executionError;
    }
    
    // Add assistant response to thread (only if we have a valid result)
    if (conversationId && result && result.finalOutput) {
      addToThread(conversationId, 'assistant', result.finalOutput);
    }
    
    console.log('========= ORCHESTRATOR COMPLETE =========\n');
    
    // Complete feedback tracking for successful operation
    try {
      const outcome = {
        success: true,
        summary: typeof result === 'string' ? result.substring(0, 200) : 'Operation completed successfully',
        confidence: 0.9
      };
      
      const analysis = await feedbackLoop.completeOperation(operationId, true, outcome);
      
      // Learn from this operation if we used adaptive context
      if (orchestratorContext.adaptiveContext || bulkOperationState.adaptiveContext) {
        const { learnFromOperation } = await import('./context/adaptive-context-builder.js');
        await learnFromOperation(message, orchestratorContext, outcome);
      }
      
      // Apply learning from context usage
      if (analysis && analysis.efficiency > 0.7) {
        const { learnFromContextUsage } = await import('./agents/context-analyzer-mini.js');
        await learnFromContextUsage(message, orchestratorContext.fetchedContext || {}, outcome);
      }
      
      console.log(`[FeedbackLoop] Operation completed with ${Math.round((analysis?.efficiency || 0.5) * 100)}% context efficiency`);
    } catch (feedbackError) {
      console.error('[FeedbackLoop] Failed to complete tracking:', feedbackError);
    }
    
    return result;
  } catch (error) {
    // Track error for feedback loop
    try {
      if (feedbackLoop && operationId) {
        feedbackLoop.trackError(operationId, error);
        await feedbackLoop.completeOperation(operationId, false, {
          success: false,
          error: error.message,
          summary: 'Operation failed'
        });
      }
    } catch (feedbackError) {
      console.error('[FeedbackLoop] Failed to track error:', feedbackError);
    }
    
    // Track error for progressive enhancement
    if (!error.isGuardrailError && bulkOperationState.isActive) {
      try {
        const { progressiveEnhancer } = await import('./context/progressive-enhancer.js');
        const tracking = await progressiveEnhancer.trackAttempt(
          conversationId,
          message,
          fullResponse || '',
          error.message
        );
        
        if (tracking.needsEnhancement && tracking.attemptCount <= 3) {
          console.log('[Orchestrator] Progressive enhancement triggered after', tracking.attemptCount, 'attempts');
          
          // Enhance the context
          const enhancedContext = await progressiveEnhancer.enhance(
            message,
            orchestratorContext,
            tracking.analysis
          );
          
          // Update bulk operation state with enhanced context
          bulkOperationState.adaptiveContext = enhancedContext;
          
          // Retry with enhanced context
          console.log('[Orchestrator] Retrying with enhanced context...');
          const retryResult = await runDynamicOrchestrator(message, {
            conversationId,
            userId,
            sseEmitter,
            taskUpdater,
            abortSignal,
            contextOverride: enhancedContext
          });
          
          // Learn from the outcome
          await progressiveEnhancer.updatePatternEffectiveness(message, {
            success: true,
            summary: 'Enhanced context helped resolve the issue'
          });
          
          return retryResult;
        }
      } catch (enhanceError) {
        console.error('[Orchestrator] Progressive enhancement failed:', enhanceError);
      }
    }
    
    // Handle guardrail tripwire errors specially
    if (error instanceof OutputGuardrailTripwireTriggered) {
      console.log('[Guardrail] 🚫 Output guardrail blocked premature return - FORCING CONTINUATION');
      console.log('[Guardrail] Tripwire reason:', error.message);
      console.log('[Guardrail] Error type:', error.constructor.name);
      console.log('[Guardrail] DEBUG - fullResponse variable check:');
      
      // DEBUG: Check if fullResponse exists in scope
      try {
        console.log('[Guardrail] fullResponse type:', typeof fullResponse);
        console.log('[Guardrail] fullResponse length:', fullResponse?.length);
        console.log('[Guardrail] fullResponse defined:', fullResponse !== undefined);
      } catch (scopeError) {
        console.log('[Guardrail] ERROR accessing fullResponse:', scopeError.message);
        console.log('[Guardrail] Scope error type:', scopeError.constructor.name);
        // Fallback: set fullResponse to empty string if not defined
        var fullResponse = '';
        console.log('[Guardrail] Set fallback fullResponse');
      }
      
      // Preserve BOTH streamed content AND blocked output
      let preservedContent = '';
      
      // First priority: Use accumulated streaming response if available
      if (typeof fullResponse === 'string' && fullResponse.trim().length > 0) {
        // Prevent extremely long content that causes API errors
        const trimmedResponse = fullResponse.trim();
        if (trimmedResponse.length > 50000) {
          preservedContent = trimmedResponse.substring(0, 50000) + '\n\n[Content truncated to prevent API limits]';
          console.log('[Guardrail] Preserving truncated streamed content (was too long):', trimmedResponse.length, 'chars');
        } else {
          preservedContent = trimmedResponse;
          console.log('[Guardrail] Preserving streamed content:', preservedContent.substring(0, 100) + '...');
        }
      } 
      // Fallback: Use blocked agent output from error
      else if (error.agentOutput || error.output) {
        preservedContent = error.agentOutput || error.output || '';
        console.log('[Guardrail] Preserving blocked output from error');
      }
      // Last resort: Generic message
      else {
        preservedContent = 'Previous agent work (details blocked by guardrail)';
        console.log('[Guardrail] No content found - using generic message');
      }
      
      // For bulk operations, we want to force the agent to continue working
      console.log('[Guardrail] Bulk operation incomplete - forcing agent to continue processing');
      
      // Check retry limit to prevent infinite loops
      if (bulkOperationState.retryCount >= bulkOperationState.maxRetries) {
        console.log(`[Guardrail] Max retries (${bulkOperationState.maxRetries}) exceeded - terminating bulk operation`);
        bulkOperationState.isActive = false;
        return `${preservedContent}\n\n[SYSTEM] Bulk operation terminated after ${bulkOperationState.maxRetries} retry attempts. The agent repeatedly tried to return control prematurely.`;
      }
      
      bulkOperationState.retryCount++;
      console.log(`[Guardrail] Retry attempt ${bulkOperationState.retryCount}/${bulkOperationState.maxRetries}`);
      
      try {
        if (sseEmitter) {
          sseEmitter('agent_status', { 
            status: 'guardrail_enforced', 
            message: `Bulk operation enforcement - forcing continuation (attempt ${bulkOperationState.retryCount})` 
          });
        }
      } catch (sseError) {
        console.log('[Guardrail] SSE emission failed:', sseError.message);
      }
      
      // FORCE CONTINUATION: Create a continuation prompt that preserves the streamed content
      let bulkItemsContext = '';
      let remainingItems = [];
      
      // Use checkpoint data to skip completed items
      if (bulkOperationState.checkpoints.length > 0) {
        const lastCheckpoint = bulkOperationState.checkpoints[bulkOperationState.checkpoints.length - 1];
        const completedSet = new Set(lastCheckpoint.completed?.map(c => c.item) || []);
        
        // Filter out completed items
        if (bulkOperationState.itemList && bulkOperationState.itemList.length > 0) {
          remainingItems = bulkOperationState.itemList.filter((item, idx) => {
            const itemIdentifier = typeof item === 'object' ? 
              (item.title || item.description || `item_${idx}`) : item;
            return !completedSet.has(itemIdentifier);
          });
          
          console.log(`[Guardrail] Using checkpoint data: ${completedSet.size} items completed, ${remainingItems.length} remaining`);
        }
      } else if (bulkOperationState.itemList && bulkOperationState.itemList.length > 0) {
        // Fallback to simple slice if no checkpoints
        remainingItems = bulkOperationState.itemList.slice(bulkOperationState.completedItems);
      }
      
      if (remainingItems.length > 0) {
        bulkItemsContext = `\n\nREMAINING ITEMS TO PROCESS:\n${remainingItems.map((item, idx) => 
          `${idx + 1}. ${typeof item === 'object' ? (item.description || JSON.stringify(item)) : item}`
        ).join('\n')}\n`;
      }
      
      // Build continuation prompt using original context + guardrail enforcement
      let continuationPrompt = '';
      
      // If we have the original contextual message, use it as the base
      if (global.currentOriginalContextualMessage) {
        console.log('[Guardrail] Using original contextual message for retry');
        continuationPrompt = global.currentOriginalContextualMessage + `

[PREVIOUS WORK COMPLETED BY AGENT] 
${preservedContent}

[GUARDRAIL ENFORCEMENT] The bulk operation is INCOMPLETE. You attempted to return control to the user, but this is prohibited during bulk operations.

MANDATORY NEXT ACTION: You MUST continue processing the remaining items from the bulk operation using ONLY the available MCP tools.
${bulkItemsContext}
CRITICAL TOOL REQUIREMENTS:
- Use python_tools_agent to execute Shopify operations directly
- When calling python_tools_agent, PASS THE BULK ITEMS in the context parameter:
  context: {
    bulk_items: ${remainingItems.length > 0 ? JSON.stringify(remainingItems) : '[remaining items]'},
    bulk_operation_type: "${bulkOperationState.operationType || 'update'}",
    bulk_progress: { total: ${bulkOperationState.expectedItems}, completed: ${bulkOperationState.completedItems}, current_index: ${bulkOperationState.completedItems} },
    adaptive_context: ${bulkOperationState.adaptiveContext ? JSON.stringify({
      tokenCount: bulkOperationState.adaptiveContext.tokenCount,
      hasExtractedData: !!bulkOperationState.adaptiveContext.extractedData,
      fetchedContextKeys: Object.keys(bulkOperationState.adaptiveContext.fetchedContext || {})
    }) : 'null'}
  }
- Use search_products, get_product, update_pricing MCP tools (NOT bash/CLI commands)
- DO NOT use non-existent "shopify" CLI commands
- DO NOT write Python scripts with placeholder URLs
- DO NOT make up tool capabilities

IMMEDIATE ACTION REQUIRED:
- IMMEDIATELY call python_tools_agent for the next unprocessed item
- DO NOT ask "what would you like me to do next"
- DO NOT request permission to continue
- DO NOT provide options or choices
- IF task is completed, and you are certain of it, mark it as completed.

Expected items remaining: ${Math.max(0, bulkOperationState.expectedItems - bulkOperationState.completedItems)}

CONTINUE NOW with the next item using proper MCP tools.`;
      } else {
        // Fallback to just the guardrail message if no original context
        console.log('[Guardrail] WARNING: No original context found, using minimal retry prompt');
        continuationPrompt = `[Conversation ID: ${conversationId}]

User: ${global.currentBaseMessage || 'Continue bulk operation'}

[PREVIOUS WORK COMPLETED] 
${preservedContent}

[GUARDRAIL ENFORCEMENT] The bulk operation is INCOMPLETE. You attempted to return control to the user, but this is prohibited during bulk operations.

MANDATORY NEXT ACTION: You MUST continue processing the remaining items from the bulk operation using ONLY the available MCP tools.
${bulkItemsContext}
CRITICAL TOOL REQUIREMENTS:
- Use python_tools_agent to execute Shopify operations directly
- When calling python_tools_agent, PASS THE BULK ITEMS in the context parameter:
  context: {
    bulk_items: ${remainingItems.length > 0 ? JSON.stringify(remainingItems) : '[remaining items]'},
    bulk_operation_type: "${bulkOperationState.operationType || 'update'}",
    bulk_progress: { total: ${bulkOperationState.expectedItems}, completed: ${bulkOperationState.completedItems}, current_index: ${bulkOperationState.completedItems} },
    adaptive_context: ${bulkOperationState.adaptiveContext ? JSON.stringify({
      tokenCount: bulkOperationState.adaptiveContext.tokenCount,
      hasExtractedData: !!bulkOperationState.adaptiveContext.extractedData,
      fetchedContextKeys: Object.keys(bulkOperationState.adaptiveContext.fetchedContext || {})
    }) : 'null'}
  }

Expected items remaining: ${Math.max(0, bulkOperationState.expectedItems - bulkOperationState.completedItems)}

CONTINUE NOW with the next item using proper MCP tools.`;
      }

      console.log('[Guardrail] 🔄 FORCING RETRY with continuation prompt');
      
      // Recursively call the orchestrator with continuation prompt
      try {
        const retryResult = await runDynamicOrchestrator(continuationPrompt, {
          conversationId,
          userId,
          sseEmitter,
          taskUpdater,
          abortSignal
        });
        
        // If retry succeeds, preserve the streamed content in the final result
        if (typeof retryResult === 'string') {
          return `${preservedContent}\n\n${retryResult}`;
        }
        
        return retryResult;
      } catch (retryError) {
        console.log('[Guardrail] Retry failed:', retryError.message);
        
        // If retry fails, mark bulk operation as done to prevent infinite loops
        bulkOperationState.isActive = false;
        
        return `${preservedContent}\n\n[SYSTEM] Guardrail enforced continuation but retry failed: ${retryError.message}. Bulk operation terminated to prevent infinite loop.`;
      }
    }
    
    if (error instanceof InputGuardrailTripwireTriggered) {
      console.log('[Guardrail] 🚫 Input guardrail blocked request');
      console.log('[Guardrail] Reason:', error.message);
      
      if (sseEmitter) {
        sseEmitter('agent_status', { 
          status: 'guardrail_blocked', 
          message: 'Request blocked by input guardrail' 
        });
      }
      
      return 'Request blocked by safety guardrail.';
    }
    
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
    global.currentBaseMessage = null;
    global.currentOriginalContextualMessage = null;
    // Clear abort signal reference
    currentAbortSignal = null;
    global.currentAbortSignal = null;
    // Clear image data
    global.currentImageData = null;
    global.currentUserImage = null;
    
    // Clear guardrail state
    bulkOperationState.isActive = false;
    bulkOperationState.expectedItems = 0;
    bulkOperationState.completedItems = 0;
    bulkOperationState.itemList = [];
    bulkOperationState.conversationId = null;
    bulkOperationState.retryCount = 0;
  }
}