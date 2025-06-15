import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { MCPServerStdio } from '@openai/agents';
import { readFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { generateTodosTool, getTodosTool, updateTaskStatusTool } from './task-generator-agent.js';

// Debug logging for startup
console.log('======= BASIC-AGENT-UNIFIED.JS INITIALIZATION =======');
console.log('OPENAI_API_KEY available:', !!process.env.OPENAI_API_KEY);
console.log('MCP_BEARER_TOKEN available:', !!process.env.MCP_BEARER_TOKEN);

// Set the OpenAI API key for the agent to use
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);
console.log('Set default OpenAI API key');

// --- Shopify MCP server configuration ---
let shopifyMCPServer = null;
if (process.env.SKIP_MCP_DISCOVERY === 'true') {
  console.log('⚠️ SKIP_MCP_DISCOVERY=true – skipping Shopify MCP server connection');
} else {
  const childEnv = { ...process.env };
  shopifyMCPServer = new MCPServerStdio({
    name: 'Shopify MCP Server',
    command: '/home/pranav/.nvm/versions/node/v22.13.0/bin/npx',
    args: ['-y', '@pranavchavda/shopify-mcp-stdio-client'],
    env: childEnv,
    shell: true,
    cacheToolsList: true,
  });
  await shopifyMCPServer.connect();
  console.log('Configured Shopify MCP Server');
}

// --- Todo MCP server configuration ---
// Removed todoMCPServer configuration

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
let espressoSystemPrompt = readFileSync(new URL('./espresso-system-prompt.txt', import.meta.url), 'utf-8');
//add today's date to the system prompt
espressoSystemPrompt += '\nToday is ' + new Date().toLocaleDateString();



// Create the unified agent that handles both planning and execution
export const unifiedAgent = new Agent({
  name: 'EspressoBot',
  instructions: espressoSystemPrompt,
  handoffDescription: 'You are an expert at executing your mission: which is to perform catalog and storefront tasks flawlessly, quickly, and with zero guesswork.',
  model: process.env.OPENAI_MODEL || 'gpt-4.1',
  modelSettings: { 
    temperature: 0.7,
    parallelToolCalls: false,  // Disabled to prevent multiple simultaneous generate_todos calls
    toolChoice: 'auto',  // Changed from 'required' to avoid forcing tool use on every turn
  },
  mcpServers: shopifyMCPServer ? [shopifyMCPServer] : [],
  tools: [generateTodosTool, getTodosTool, updateTaskStatusTool],
});

// Note: Loop prevention for generate_todos is handled in unified-orchestrator.js via onStepStart hook
// The Agent class doesn't support event listeners like .on('tool_call_start')
// This non-working code has been removed to avoid confusion

console.log('Created unified agent with direct MCP integration');
console.log('======= BASIC-AGENT-UNIFIED.JS INITIALIZATION COMPLETE =======');

export { shopifyMCPServer };