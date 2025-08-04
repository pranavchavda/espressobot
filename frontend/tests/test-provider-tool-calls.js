#!/usr/bin/env node

// Test tool execution with Anthropic and OpenRouter providers

import { Agent, run } from '@openai/agents';
import { tool } from '@openai/agents';
import { z } from 'zod';
import { AnthropicProvider } from '../server/models/anthropic-provider.js';
import { OpenRouterProvider } from '../server/models/openrouter-provider.js';

// Create a simple test tool
const testTool = tool({
  name: 'get_weather',
  description: 'Get the current weather for a location',
  parameters: z.object({
    location: z.string().describe('The city and state, e.g. San Francisco, CA'),
    unit: z.enum(['celsius', 'fahrenheit']).optional().default('fahrenheit')
  }),
  execute: async ({ location, unit }) => {
    console.log(`[TOOL EXECUTED] Getting weather for ${location} in ${unit}`);
    return {
      location,
      temperature: unit === 'celsius' ? 22 : 72,
      conditions: 'Sunny',
      unit
    };
  }
});

async function testProvider(providerName, provider, modelName) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`Testing ${providerName} with model: ${modelName}`);
  console.log('='.repeat(60));
  
  try {
    // Create agent with the custom provider
    const agent = new Agent({
      name: `Test_${providerName}_Agent`,
      instructions: `You are a helpful weather assistant. When asked about weather, use the get_weather tool to provide accurate information. Always use the tool when asked about weather conditions.`,
      model: provider.getModel(modelName),
      tools: [testTool]
    });
    
    // Test messages
    const testMessages = [
      "What's the weather like in New York, NY?",
      "Tell me the temperature in London, UK in celsius",
      "Is it sunny in Tokyo, Japan?"
    ];
    
    for (const message of testMessages) {
      console.log(`\n📝 User: ${message}`);
      
      let toolCalled = false;
      let assistantResponse = '';
      
      try {
        const result = await run(agent, message, {
          onStepStart: (step) => {
            if (step.tool_name) {
              console.log(`🔧 Tool call started: ${step.tool_name}`);
              toolCalled = true;
            }
          },
          onStepFinish: (step) => {
            if (step.tool_name && step.result) {
              console.log(`✅ Tool result:`, JSON.stringify(step.result, null, 2));
            }
          },
          onMessage: (msg) => {
            if (msg.content) {
              assistantResponse = msg.content;
            }
          }
        });
        
        console.log(`🤖 Assistant: ${assistantResponse || result}`);
        
        if (!toolCalled) {
          console.log(`⚠️  WARNING: Tool was not called for this query!`);
        }
        
      } catch (error) {
        console.error(`❌ Error processing message:`, error.message);
      }
    }
    
    console.log(`\n✅ ${providerName} test completed`);
    
  } catch (error) {
    console.error(`\n❌ ${providerName} test failed:`, error.message);
    console.error(error.stack);
  }
}

async function runTests() {
  console.log('🧪 Testing Custom Provider Tool Execution\n');
  
  // Test Anthropic provider
  if (process.env.ANTHROPIC_API_KEY) {
    const anthropicProvider = new AnthropicProvider();
    await testProvider('Anthropic', anthropicProvider, 'claude-3-5-sonnet-20241022');
  } else {
    console.log('⚠️  Skipping Anthropic test - ANTHROPIC_API_KEY not set');
  }
  
  // Test OpenRouter provider
  if (process.env.OPENROUTER_API_KEY) {
    const openRouterProvider = new OpenRouterProvider();
    // Test with different models
    await testProvider('OpenRouter-Claude', openRouterProvider, 'anthropic/claude-3.5-sonnet');
    await testProvider('OpenRouter-GPT4', openRouterProvider, 'openai/gpt-4-turbo-preview');
  } else {
    console.log('⚠️  Skipping OpenRouter test - OPENROUTER_API_KEY not set');
  }
  
  // Test with regular OpenAI for comparison
  console.log(`\n${'='.repeat(60)}`);
  console.log('Testing OpenAI (baseline comparison)');
  console.log('='.repeat(60));
  
  try {
    const openAIAgent = new Agent({
      name: 'Test_OpenAI_Agent',
      instructions: `You are a helpful weather assistant. When asked about weather, use the get_weather tool to provide accurate information.`,
      model: 'gpt-4-turbo-preview',
      tools: [testTool]
    });
    
    const result = await run(openAIAgent, "What's the weather in Paris, France?", {
      onStepStart: (step) => {
        if (step.tool_name) {
          console.log(`🔧 Tool call started: ${step.tool_name}`);
        }
      },
      onStepFinish: (step) => {
        if (step.tool_name && step.result) {
          console.log(`✅ Tool result:`, JSON.stringify(step.result, null, 2));
        }
      }
    });
    
    console.log(`🤖 Assistant response received`);
    console.log('✅ OpenAI baseline test completed');
    
  } catch (error) {
    console.error('❌ OpenAI test failed:', error.message);
  }
  
  console.log('\n🏁 All tests completed!');
}

// Run the tests
runTests().catch(console.error);