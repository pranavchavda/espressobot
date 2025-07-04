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
import path from 'path';
import { analyzeIntent } from './tools/intent-analyzer.js';
import { 
  addToThread, 
  getAutonomyRecommendation, 
  formatThreadForAgent 
} from './tools/conversation-thread-manager.js';
import { getSmartContext } from './context-loader/context-manager.js';
import { memoryOperations } from './memory/memory-operations-local.js';
import { initializeMCPTools, callMCPTool, getMCPTools } from './tools/mcp-client.js';
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

// Task Manager Agent removed - functionality merged into Task Planning Agent

/**
 * Build rich context object for agents
 * This is the ONLY place where RAG/memory access happens
 */
async function buildAgentContext(options) {
  const { 
    task, 
    conversationId, 
    userId, 
    userMessage, 
    autonomyLevel,
    additionalContext 
  } = options;
  
  console.log(`[ORCHESTRATOR] Building context for task: ${task.substring(0, 100)}...`);
  
  const context = {
    task,
    conversationId,
    userId,
    autonomyLevel,
    specificEntities: [],
    relevantMemories: [],
    relevantRules: [],
    relevantTools: [],
    conversationHistory: [],
    currentTasks: [],
    stateTracking: {},
    businessLogic: {}
  };
  
  // Extract specific entities from the task (products, SKUs, prices)
  const entityPatterns = {
    products: /https:\/\/idrinkcoffee\.com\/products\/[\w-]+/g,
    skus: /\b[A-Z]{2,}-?\d{3,}[A-Z]?\b/g,
    prices: /\$?\d+\.?\d*(?:\s*(?:CAD|USD))?/g,
    handles: /["']?([\w-]+)["']?\s*(?:handle|product)/gi
  };
  
  for (const [type, pattern] of Object.entries(entityPatterns)) {
    const matches = task.match(pattern) || [];
    if (matches.length > 0) {
      context.specificEntities.push({
        type,
        values: [...new Set(matches)]
      });
    }
  }
  
  // Get smart context (rules, tools, workflows)
  try {
    const smartContext = await getSmartContext(task, {
      includeMemory: false, // We'll handle memory separately
      userId: userId ? `user_${userId}` : null,
      conversationId
    });
    
    // Parse smart context sections
    const sections = smartContext.split(/\n## /);
    for (const section of sections) {
      if (section.includes('Business Rules')) {
        context.relevantRules = section.split('\n').filter(line => line.trim());
      } else if (section.includes('Tools')) {
        context.relevantTools = section.split('\n').filter(line => line.trim());
      } else if (section.includes('Conversation Topic')) {
        context.conversationTopic = section.trim();
      }
    }
  } catch (error) {
    console.log(`[ORCHESTRATOR] Error loading smart context:`, error.message);
  }
  
  // Search for relevant memories
  if (userId) {
    try {
      const memories = await memoryOperations.search(task, `user_${userId}`, 5);
      context.relevantMemories = memories.map(m => ({
        content: m.memory,
        score: m.score,
        metadata: m.metadata
      }));
    } catch (error) {
      console.log(`[ORCHESTRATOR] Error searching memories:`, error.message);
    }
  }
  
  // Get conversation thread history
  if (conversationId) {
    context.conversationHistory = formatThreadForAgent(conversationId, 10);
    
    // Get current tasks
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
  
  // Analyze for business logic patterns
  context.businessLogic = analyzeBusinessLogic(task, userMessage);
  
  // Add any additional context
  if (additionalContext) {
    context.additionalContext = additionalContext;
  }
  
  return context;
}

/**
 * Analyze task for business logic patterns
 */
function analyzeBusinessLogic(task, fullMessage) {
  const logic = {
    patterns: [],
    warnings: []
  };
  
  // Discount removal pattern
  if (/remove.*discount|set.*base.*price.*compare/i.test(task)) {
    logic.patterns.push({
      type: 'discount_removal',
      action: 'Set base price to compare_at_price value',
      warning: 'Preserve original compare_at_price before updating'
    });
  }
  
  // Bulk operation pattern
  const bulkMatch = task.match(/(\d+)\+?\s*(?:products?|items?)/i);
  if (bulkMatch && parseInt(bulkMatch[1]) > 10) {
    logic.patterns.push({
      type: 'bulk_operation',
      itemCount: parseInt(bulkMatch[1]),
      warning: 'High-impact operation affecting many items'
    });
  }
  
  // Price update pattern
  if (/update.*price|change.*price|set.*price/i.test(task)) {
    logic.patterns.push({
      type: 'price_update',
      action: 'Update product pricing',
      reminder: 'Check for compare_at_price to maintain discount structure'
    });
  }
  
  return logic;
}

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
    autonomyLevel: z.enum(['high', 'medium', 'low']).optional().default('high').describe('Autonomy level - high: execute without confirmation, medium: confirm risky operations, low: confirm all writes'),
    // NEW: Allow orchestrator to pass curated context
    curatedContext: z.string().nullable().optional().describe('JSON-encoded curated context that orchestrator decides to share with this agent')
  }),
  execute: async ({ agentName, task, context, useSemanticSearch, autonomyLevel, curatedContext }) => {
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
        ...(parsedContext && typeof parsedContext === 'object' && !Array.isArray(parsedContext) ? parsedContext : {})
      };
      if (parsedContext && typeof parsedContext === 'object' && !Array.isArray(parsedContext)) {
        console.log(`[ORCHESTRATOR] Curated context includes: ${Object.keys(parsedContext).join(', ')}`);
      } else {
        console.log(`[ORCHESTRATOR] Curated context type: ${typeof parsedContext}`);
      }
    } else {
      // Fallback: Build minimal context
      console.log(`[ORCHESTRATOR] No curated context provided, using minimal context`);
      richContext = {
        task,
        conversationId,
        userId,
        autonomyLevel: effectiveAutonomy,
        specificEntities: [],
        relevantMemories: [],
        relevantRules: [],
        businessLogic: {},
        currentTasks: [],
        additionalContext: context
      };
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
      autonomyLevel: z.enum(['high', 'medium', 'low']).optional().default('high'),
      curatedContext: z.string().nullable().optional()
    })).describe('Array of tasks to run in parallel, each with optional curated context')
  }),
  execute: async ({ tasks }) => {
    console.log(`[ORCHESTRATOR] Spawning ${tasks.length} bash agents in parallel`);
    
    // Create and run all agents in parallel
    const promises = tasks.map(async ({ agentName, task, context, autonomyLevel, curatedContext }) => {
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
          ...(parsedContext && typeof parsedContext === 'object' && !Array.isArray(parsedContext) ? parsedContext : {}),
          additionalContext: context
        };
      } else {
        richContext = {
          task,
          conversationId,
          userId,
          autonomyLevel: effectiveAutonomy,
          specificEntities: [],
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
          if (schema.items?.type === 'string') {
            zodSchema = z.array(z.string());
          } else if (schema.items?.type === 'number') {
            zodSchema = z.array(z.number());
          } else if (schema.items?.type === 'object') {
            // For object arrays, create a proper object schema
            const itemSchema = {};
            if (schema.items.properties) {
              Object.entries(schema.items.properties).forEach(([itemKey, itemProp]) => {
                if (itemProp.type === 'string') {
                  itemSchema[itemKey] = z.string();
                } else if (itemProp.type === 'number') {
                  itemSchema[itemKey] = z.number();
                } else if (Array.isArray(itemProp.type) && itemProp.type.includes('null')) {
                  const nonNullType = itemProp.type.find(t => t !== 'null');
                  if (nonNullType === 'string') {
                    itemSchema[itemKey] = z.string().nullable();
                  } else if (nonNullType === 'number') {
                    itemSchema[itemKey] = z.number().nullable();
                  }
                } else {
                  itemSchema[itemKey] = z.any();
                }
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
          zodSchema = zodSchema.nullable();
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
      try {
        const result = await callMCPTool(toolDef.name, args);
        return result;
      } catch (error) {
        console.error(`[Orchestrator] MCP tool ${toolDef.name} failed:`, error);
        throw error;
      }
    }
  });
}

/**
 * Build orchestrator with MCP tools
 */
async function buildOrchestratorWithMCPTools() {
  const builtInSearchTool = webSearchTool();
  
  // Initialize MCP tools
  let mcpTools = [];
  try {
    await initializeMCPTools();
    const toolDefs = await getMCPTools();
    console.log(`[Orchestrator] Loading ${toolDefs.length} MCP tools...`);
    
    // Debug: log first tool schema
    if (toolDefs.length > 0) {
      console.log('[Orchestrator] First tool schema:', JSON.stringify(toolDefs[0], null, 2));
    }
    
    // Create tool wrappers - temporarily exclude complex schema tools  
    const excludeTools = ['add_product_images', 'add_variants_to_product', 'create_full_product', 'update_full_product'];
    const filteredToolDefs = toolDefs.filter(tool => !excludeTools.includes(tool.name));
    mcpTools = filteredToolDefs.map(createMCPToolWrapper);
    console.log(`[Orchestrator] Excluded ${excludeTools.length} complex schema tools, using ${filteredToolDefs.length} tools`);
    console.log(`[Orchestrator] MCP tools loaded successfully:`, toolDefs.map(t => t.name).join(', '));
  } catch (error) {
    console.error('[Orchestrator] Failed to load MCP tools:', error.message);
    console.error('[Orchestrator] Error stack:', error.stack);
    // Continue without MCP tools
  }
  
  return new Agent({
  name: 'Dynamic_Bash_Orchestrator',
  model: 'o3',  // Back to OpenAI for now
  

  instructions: `# EspressoBot Orchestrator

You orchestrate the iDrinkCoffee.com e-commerce operations by analyzing requests and delegating to specialized agents.

## CRITICAL: Three-Step Context Process
1. **BUILD CONTEXT FOR YOURSELF** - The system has already built comprehensive context including entities, business patterns, memories, and current tasks
2. **USE CONTEXT FOR DECISIONS** - Analyze the provided context to understand what needs to be done and how
3. **CURATE CONTEXT FOR AGENTS** - Manually select what context each agent needs using the curatedContext parameter

## Your Context (Already Built)
You receive rich context in your message including:
- **Entities Detected**: Products, URLs, SKUs, prices extracted from the request
- **Business Patterns**: Recognized operations like price updates, bulk changes, etc.
- **Current Tasks**: Any existing tasks for this conversation
- **Relevant Past Experiences**: Memories from similar past operations
- **Conversation Topic**: The identified topic/goal of this conversation

Access your full context via: global.orchestratorContext
This contains: specificEntities, businessLogic, relevantMemories, relevantRules, currentTasks, etc.

## Context Curation Rules
When spawning agents, YOU MUST use the curatedContext parameter to manually select what they need. Pass an object with only the relevant fields:

Example curatedContext values (pass as JSON strings):
- For price updates: JSON.stringify({ specificEntities: [/* products, prices */], relevantRules: [/* pricing rules */] })
- For bulk operations: JSON.stringify({ specificEntities: [/* all affected items */], businessLogic: { patterns: [...], warnings: [...] } })
- For tool creation: JSON.stringify({ relevantMemories: [/* similar tool experiences */] })
- For task execution: JSON.stringify({ currentTasks: [/* tasks array */] })
- For simple lookups: null

NEVER pass your entire context - be selective based on the specific task

## CRITICAL: Autonomy-First Execution
- The system has already analyzed the user's intent and determined the appropriate autonomy level
- Access the analysis via global.currentIntentAnalysis (level: high/medium/low, reason, confidence)
- **ALWAYS pass the analyzed autonomy level to spawned agents**
- Default to 'high' autonomy unless the analysis suggests otherwise

## Task Planning Guidelines
- Use task_planner ONLY for genuinely complex multi-step requests
- DO NOT use task_planner for simple operations with specific values
- Examples needing planning: "migrate all products to new system", "create full product catalog report"
- Examples NOT needing planning: "update price to $49.99", "add products X,Y,Z to collection"
- When using task_planner, YOU decide what context to pass - include specific entities, constraints, or patterns you've identified

## Execution Rules
- **High Autonomy (default)**: User provided specific values or clear commands
  - Pass autonomy='high' to agents - they will execute immediately
  - Examples: "Update SKU123 to $49.99", "Set products A,B,C to active"
- **Medium Autonomy**: High-risk operations detected
  - Pass autonomy='medium' to agents - they'll confirm only risky operations
  - Examples: Operations affecting 50+ items, bulk deletes
## MOST IMPORTANT: Workflow rule:
- Your role is to be a "headless" orchestrator. You receive a task, create a plan, and execute it using bash agents.
- You are NOT a conversational chatbot. Your primary output MUST be tool calls, not text.
- AVOID ALL conversational replies like "Understood," "Okay," or "I will start on that." Do not confirm receipt of instructions.
- ONLY generate text output if you are asking a critical clarifying question that you cannot answer otherwise, or when the final product of the entire user request is ready.
- Acknowledge instructions by immediately using a tool. This is your way of confirming the task.
- You DO NOT need to update the user on your progress. The user sees progress via UI events from your tool calls.
- Only update the user when you are done orchestrating, or if you need to ask for information for which you have no other way of obtaining.

## Agent Capabilities

### Bash Agents CAN:
- Execute all Python tools (run_graphql_query, update_pricing, etc.)
- Access live Shopify data and perform mutations
- Update task status
- Work autonomously based on the autonomy level you pass

### MCP Tools Available:
You have 27 native MCP tools loaded - ALWAYS use these FIRST before considering bash agents:

**CRITICAL: Use MCP tools directly for ALL simple operations:**

**Products (12 tools):**
- get_product: Get product details by SKU/handle/ID
- get_product_native: Native MCP implementation 
- search_products: Search with filters
- create_product: Create basic products
- create_full_product: Create products with all features
- create_combo: Create machine+grinder combos
- create_open_box: Create open box listings
- update_full_product: Comprehensive product updates
- update_status: Change product status
- add_variants_to_product: Add variants to existing products
- manage_tags: Add/remove product tags
- manage_variant_links: Link related product variants

**Pricing & Inventory (3 tools):**
- update_pricing: Update individual product pricing
- bulk_price_update: Update prices for multiple products
- manage_inventory_policy: Control overselling settings

**Media & Store (2 tools):**
- add_product_images: Manage product images
- manage_redirects: Create/manage URL redirects

**Sales & Marketing (3 tools):**
- manage_map_sales: Breville MAP sales calendar
- manage_miele_sales: Miele MAP sales calendar
- send_review_request: Send Yotpo review emails

**Technical (5 tools):**
- graphql_query: Execute raw GraphQL queries
- graphql_mutation: Execute raw GraphQL mutations
- perplexity_research: AI-powered research tool
- memory_operations: Local memory system access

**SkuVault & Features (3 tools):**
- upload_to_skuvault: Upload products to SkuVault
- manage_skuvault_kits: Manage product kits/bundles
- manage_features_metaobjects: Manage product features via metaobjects

**Only spawn bash agents for genuinely complex multi-step workflows, file operations, or non-MCP tasks.**

### How to Instruct Bash Agents (for complex tasks):
When you DO need bash agents for non-MCP tasks, BE SPECIFIC! Tell them EXACTLY what to run:

**Use bash agents for:**
- File system operations (git, file manipulation, etc.)
- Multi-step workflows requiring complex logic
- Non-Shopify system tasks
- Legacy tools not yet migrated to MCP

**Examples:**
- ❌ BAD: "Update inventory policy for variant 123 to DENY" (This is an MCP tool!)
- ✅ GOOD: "Use MCP tool directly: manage_inventory_policy(identifier='123', policy='deny')"
- ✅ GOOD: "Run git operations: git status && git add . && git commit -m 'Update'"
- ✅ GOOD: "Run legacy tool: python3 /path/to/non-mcp-tool.py --args"

### Bash Agents CANNOT:
- Access MCP (documentation, schema introspection)
- Use Context7 or Shopify Dev docs

### SWE Agent CAN:
- Create/modify tools
- Access MCP for documentation and schema
- Perform software engineering tasks

## Decision Tree with Context Curation Examples
CRITICAL: curatedContext must ALWAYS be a JSON string or null!

**STEP 1: ALWAYS try MCP tools FIRST for simple operations**

Before spawning any bash agents, check if you can use MCP tools directly:

✅ **USE MCP TOOLS DIRECTLY FOR:**
- get_product(identifier="mexican-altura") ← USE THIS for "Get product details for mexican-altura"
- search_products(query="coffee", limit=10)
- manage_inventory_policy(identifier="31480448974882", policy="deny")
- update_pricing(sku="ESP-1001", price=49.99)
- create_product(title="...", vendor="...", product_type="...")
- manage_tags(product="...", tags="...", action="add")

**STEP 2: Only spawn bash agents for non-MCP tasks:**
   - File operations, git, system tasks, or complex multi-step workflows
   - Be SPECIFIC in the task description - tell the agent EXACTLY what to run
   - Example task: "Run git commands: git status && git add . && git commit -m 'message'"
   - Example task: "Process CSV file with custom logic: python3 /path/to/custom-script.py /tmp/data.csv"
   - curatedContext: JSON.stringify({ specificEntities: [only relevant entities], relevantRules: [only relevant rules] })
4. For genuinely complex multi-step workflows → task_planner with curated request
5. For high-risk operations → spawn_bash_agent with autonomy='medium' and:
   curatedContext: JSON.stringify({ businessLogic: {include warnings}, specificEntities: [affected items] })
6. For tool creation → swe_agent with:
   curatedContext: JSON.stringify({ relevantMemories: [memories about similar tools] })
7. For documentation → swe_agent with minimal context (curatedContext: null)
8. For multiple independent tasks → spawn_parallel_bash_agents with task-specific context for each

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
  modelSettings: {
    parallelToolCalls: true

  },
  tools: [
    ...mcpTools,  // MCP tools FIRST for priority
    builtInSearchTool,
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
        
        const result = await run(taskPlanningAgent, enhancedRequest, { maxTurns: 30 });
        
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
    tool({
      name: 'swe_agent',
      description: 'Software Engineering Agent - handoff for creating new tools, modifying existing tools, MCP access (Shopify docs, Context7), or any code-related tasks',
      parameters: z.object({
        prompt: z.string().describe('The task or request to pass to the SWE Agent'),
        curatedContext: z.string().nullable().optional().describe('JSON-encoded curated context for the SWE agent')
      }),
      execute: async ({ prompt, curatedContext }) => {
        console.log(`[ORCHESTRATOR] SWE Agent - CuratedContext type: ${typeof curatedContext}`);
        
        // Validate curatedContext
        if (curatedContext !== null && curatedContext !== undefined && typeof curatedContext !== 'string') {
          console.error(`[ORCHESTRATOR] ERROR: curatedContext must be a JSON string or null, got ${typeof curatedContext}`);
          if (typeof curatedContext === 'object') {
            curatedContext = JSON.stringify(curatedContext);
            console.log(`[ORCHESTRATOR] Converted curatedContext to JSON string`);
          }
        }
        
        // Use orchestrator's curated context or minimal context
        let context;
        if (curatedContext) {
          const parsedContext = typeof curatedContext === 'string' ? JSON.parse(curatedContext) : curatedContext;
          context = {
            task: prompt,
            conversationId: global.currentConversationId,
            userId: global.currentUserId,
            autonomyLevel: global.currentIntentAnalysis?.level || 'high',
            ...(parsedContext && typeof parsedContext === 'object' && !Array.isArray(parsedContext) ? parsedContext : {})
          };
        } else {
          context = {
            task: prompt,
            conversationId: global.currentConversationId,
            userId: global.currentUserId,
            autonomyLevel: global.currentIntentAnalysis?.level || 'high',
            specificEntities: [],
            relevantMemories: [],
            relevantRules: [],
            businessLogic: {},
            currentTasks: []
          };
        }
        
        console.log('[Orchestrator] Using curated context for SWE Agent');
        
        // Get SWE agent with orchestrator-provided context
        const sweAgent = await getSWEAgent(prompt, global.currentConversationId, context);
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
  ]
});
}

// Create the orchestrator instance
let dynamicOrchestrator = null;

/**
 * Initialize and get the orchestrator
 */
async function getOrchestrator() {
  if (!dynamicOrchestrator) {
    console.log('[Orchestrator] Building orchestrator with MCP tools...');
    dynamicOrchestrator = await buildOrchestratorWithMCPTools();
  }
  return dynamicOrchestrator;
}

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
  // Store user message globally for context building
  global.currentUserMessage = message;
  
  // BUILD RICH CONTEXT FIRST - Orchestrator needs this for decision making
  console.log(`[Orchestrator] Building comprehensive context for decision making...`);
  const orchestratorContext = await buildAgentContext({
    task: message,
    conversationId,
    userId,
    userMessage: message,
    autonomyLevel: intentAnalysis.level,
    additionalContext: null
  });
  
  // Store orchestrator's full context globally for reference
  global.orchestratorContext = orchestratorContext;
  
  // Log what we found
  console.log(`[Orchestrator] Context analysis complete:`);
  console.log(`  - Entities found: ${orchestratorContext.specificEntities.map(e => `${e.type}(${e.values.length})`).join(', ')}`);
  console.log(`  - Business patterns: ${orchestratorContext.businessLogic.patterns.map(p => p.type).join(', ')}`);
  console.log(`  - Memories: ${orchestratorContext.relevantMemories.length}`);
  console.log(`  - Current tasks: ${orchestratorContext.currentTasks.length}`);
  console.log(`  - Rules loaded: ${orchestratorContext.relevantRules.length > 0 ? 'Yes' : 'No'}`);
  
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
    
    // Add entity context if found
    if (orchestratorContext.specificEntities.length > 0) {
      contextualMessage += '\n\n## Entities Detected:';
      for (const entity of orchestratorContext.specificEntities) {
        contextualMessage += `\n- ${entity.type}: ${entity.values.join(', ')}`;
      }
    }
    
    // Add business logic patterns if detected
    if (orchestratorContext.businessLogic.patterns.length > 0) {
      contextualMessage += '\n\n## Business Patterns Detected:';
      for (const pattern of orchestratorContext.businessLogic.patterns) {
        contextualMessage += `\n- ${pattern.type}: ${pattern.action}`;
        if (pattern.warning) contextualMessage += ` (WARNING: ${pattern.warning})`;
      }
    }
    
    // Add current tasks if any
    if (orchestratorContext.currentTasks.length > 0) {
      contextualMessage += '\n\n## Current Tasks:';
      orchestratorContext.currentTasks.forEach((task, idx) => {
        const status = task.status === 'completed' ? '[x]' : 
                      task.status === 'in_progress' ? '[🔄]' : '[ ]';
        contextualMessage += `\n${idx}. ${status} ${task.title || task.description}`;
      });
    }
    
    // Add relevant memories if any
    if (orchestratorContext.relevantMemories.length > 0) {
      contextualMessage += '\n\n## Relevant Past Experiences:';
      orchestratorContext.relevantMemories.slice(0, 3).forEach(memory => {
        contextualMessage += `\n- ${memory.content}`;
      });
    }
    
    // Add conversation topic if present
    if (orchestratorContext.conversationTopic) {
      contextualMessage += '\n\n' + orchestratorContext.conversationTopic;
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
    
    // Get the orchestrator (will initialize with MCP tools if needed)
    const orchestrator = await getOrchestrator();
    
    const result = await run(orchestrator, contextualMessage, runOptions);
    
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
    global.currentUserMessage = null;
    global.currentIntentAnalysis = null;
    // Clear abort signal reference
    currentAbortSignal = null;
    global.currentAbortSignal = null;
  }
}