import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Debug logging for startup
console.log('======= BASIC-AGENT.JS INITIALIZATION =======');
console.log('OPENAI_API_KEY available:', !!process.env.OPENAI_API_KEY);

// Set the OpenAI API key for the agent to use
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);
console.log('Set default OpenAI API key');

// Create a simple agent with no MCP server or complex tools
export const basicChatAgent = new Agent({
  name: 'BasicChatbot',
  model: process.env.OPENAI_MODEL || 'gpt-4o',
  instructions: `You are a simple AI assistant for a coffee shop called iDrinkCoffee.
    
Respond to user queries in a helpful and friendly manner.
Keep your responses concise and casual.

Always respond in a friendly, helpful tone as an assistant for iDrinkCoffee shop.`
});

console.log('Created basic agent with no MCP integration');
console.log('======= BASIC-AGENT.JS INITIALIZATION COMPLETE =======');
