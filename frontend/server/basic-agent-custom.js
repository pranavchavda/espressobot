import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { readFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { generateTodosTool, getTodosTool, updateTaskStatusTool } from './task-generator-agent.js';
import { shopifyTools } from './custom-tools-definitions.js';
import { extendedShopifyTools } from './custom-tools-definitions-extended.js';

// Debug logging for startup
console.log('======= BASIC-AGENT-CUSTOM.JS INITIALIZATION =======');
console.log('OPENAI_API_KEY available:', !!process.env.OPENAI_API_KEY);

// Set the OpenAI API key for the agent to use
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);
console.log('Set default OpenAI API key');

// Load system prompt
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
let espressoSystemPrompt = readFileSync(new URL('./espresso-system-prompt.txt', import.meta.url), 'utf-8');
// Add today's date to the system prompt
espressoSystemPrompt += '\nToday is ' + new Date().toLocaleDateString();

// Custom tools are now imported from custom-tools-definitions.js
console.log(`✅ Loaded ${shopifyTools.length} custom Shopify tools`);
console.log(`✅ Loaded ${extendedShopifyTools.length} extended Shopify tools`);

// Create the unified agent that handles both planning and execution
export const unifiedAgent = new Agent({
  name: 'EspressoBot',
  instructions: espressoSystemPrompt,
  handoffDescription: 'You are an expert at executing your mission: which is to perform catalog and storefront tasks flawlessly, quickly, and with zero guesswork.',
  model: process.env.OPENAI_MODEL || 'gpt-4o',
  modelSettings: { 
    temperature: 0.7,
    parallelToolCalls: false,  // Disabled to prevent multiple simultaneous calls
    toolChoice: 'auto',  // Changed from 'required' to avoid forcing tool use on every turn
  },
  tools: [
    ...shopifyTools,  // Custom Shopify tools
    ...extendedShopifyTools,  // Extended Shopify tools
    generateTodosTool, 
    getTodosTool, 
    updateTaskStatusTool
  ],
});

console.log('Created unified agent with custom tools');
console.log('======= BASIC-AGENT-CUSTOM.JS INITIALIZATION COMPLETE =======');