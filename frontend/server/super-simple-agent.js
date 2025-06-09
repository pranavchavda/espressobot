import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import pkg from '@prisma/client';

// Debug logging for startup
console.log('======= SUPER-SIMPLE-AGENT.JS INITIALIZATION =======');
console.log('Loading environment variables');
console.log('OPENAI_API_KEY available:', !!process.env.OPENAI_API_KEY);
console.log('OPENAI_MODEL:', process.env.OPENAI_MODEL || 'gpt-4o');

// Set the OpenAI API key for the agent to use
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);
console.log('Set default OpenAI API key');

const { PrismaClient } = pkg;
const prisma = new PrismaClient();
console.log('Initialized PrismaClient');

// Simple Agent without any MCP server integration
// Following the pattern from examples/basic/hello-world.ts
export const superSimpleAgent = new Agent({
  name: 'SimpleShopifyBot',
  model: process.env.OPENAI_MODEL || 'gpt-4o',
  instructions: `You are a simple AI assistant for a coffee shop called iDrinkCoffee.
    
Respond to user queries in a helpful and friendly manner.
Keep your responses concise and casual.

Always respond in a friendly, helpful tone as an assistant for iDrinkCoffee shop.`
});

console.log('Created super simple agent WITHOUT any MCP integration');
console.log('======= SUPER-SIMPLE-AGENT.JS INITIALIZATION COMPLETE =======');
