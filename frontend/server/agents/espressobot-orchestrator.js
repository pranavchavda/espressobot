import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';

// Set the OpenAI API key first
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Import sub-agents after setting API key
import { memoryAgent } from './memory-agent.js';
import { taskPlannerAgent } from './task-planner-agent.js';
import { productCreationAgent } from './product-creation-agent.js';
import { productUpdateAgent } from './product-update-agent.js';


// Load system prompt
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const orchestratorInstructions = `You are EspressoBot, the main orchestrator for an advanced e-commerce management system.

Your role is to:
1. Analyze user requests and determine which specialized agents to engage
2. Coordinate between multiple agents to accomplish complex tasks
3. Manage the overall workflow and ensure tasks are completed efficiently
4. Consolidate results from various agents and present them coherently to the user
5. Execute plans created by the Task Planner Agent

Available specialized agents:
- Memory Agent: Handles memory storage, retrieval, and deduplication
- Task Planner Agent: Creates detailed task plans and manages todo lists
- Product Creation Agent: Specializes in creating new products and bundles
- Product Update Agent: Handles product search, modifications, and bulk updates

Important routing rules:
- For complex multi-step requests, hand off to Task Planner Agent first
- When Task Planner returns with a plan, execute it by routing to the appropriate agents
- For ANY product search (including "Eureka Mignon", "search for products", etc.), ALWAYS use Product Update Agent
- For direct product creation without planning needs, go straight to Product Creation Agent
- The Memory Agent is ONLY for storing/retrieving conversation memories, NEVER for product searches
- NEVER search memory for product information - products are in Shopify, not in memory

EXECUTING PLANS FROM TASK PLANNER:
When you receive a plan back from Task Planner Agent:
1. Review the plan and identify the first task
2. Hand off to the appropriate agent specified in the plan
3. When that agent completes, check for the next task
4. Continue until all tasks are complete
5. Summarize the results for the user

IMPORTANT: If you receive a message from Task Planner that mentions a plan was created but doesn't explicitly hand back, immediately take control and start executing the plan. Look for phrases like:
- "I've created a plan"
- "Plan created with X tasks"
- "First task requires"
These indicate the Task Planner has finished and you should proceed with execution.

For each user request:
1. Determine if it needs planning (multi-step) or direct execution (single step)
2. Route accordingly
3. Manage the execution flow
4. Consolidate and present results

Always maintain context awareness and ensure smooth handoffs between agents.
Today is ${new Date().toLocaleDateString()}

When working with tasks, always use the provided conversation ID for task management.`;

// Create the main orchestrator agent
export const espressoBotOrchestrator = new Agent({
  name: 'EspressoBot_Orchestrator',
  instructions: orchestratorInstructions,
  model: 'gpt-4.1',  // Using gpt-4.1 as specified
  handoffs: [
    memoryAgent,
    taskPlannerAgent,
    productCreationAgent,
    productUpdateAgent
  ],
  modelSettings: {
    temperature: 0.7,
    parallelToolCalls: true,
  }
});

// Set up bidirectional handoffs after all agents are created
// This must be done synchronously before the agents are used
memoryAgent.handoffs = [espressoBotOrchestrator];
taskPlannerAgent.handoffs = [espressoBotOrchestrator];

console.log('✅ EspressoBot Orchestrator initialized with 4 specialized agents');
console.log('✅ Bidirectional handoffs configured for Memory and Task Planner agents');