import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname } from 'node:path';
import { ENHANCED_ORCHESTRATOR_INSTRUCTIONS } from './enhanced-instructions.js';

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

// Use enhanced instructions with domain knowledge
const orchestratorInstructions = ENHANCED_ORCHESTRATOR_INSTRUCTIONS;

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