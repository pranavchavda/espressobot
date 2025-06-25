#!/usr/bin/env node

// Test if callbacks work with the OpenAI agents SDK

import { run } from '@openai/agents';
import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { tool } from '@openai/agents';
import { z } from 'zod';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a simple tool
const testTool = tool({
  name: 'test_tool',
  description: 'A test tool',
  parameters: z.object({
    message: z.string()
  }),
  execute: async ({ message }) => {
    console.log('[TOOL] Executing with message:', message);
    return { success: true, message: `Processed: ${message}` };
  }
});

// Create a test agent with a tool
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a test agent. When asked to test, use the test_tool with a message.',
  model: 'gpt-4.1-mini',
  tools: [testTool]
});

async function testCallbacks() {
  console.log('🧪 Testing OpenAI Agents SDK Callbacks\n');
  
  let stepStartCount = 0;
  let stepFinishCount = 0;
  let messageCount = 0;
  
  try {
    const result = await run(testAgent, 'Please test by using your tool', {
      onStepStart: (step) => {
        stepStartCount++;
        console.log(`\n[onStepStart #${stepStartCount}]`);
        console.log('- Type:', step.type);
        console.log('- Agent:', step.agent?.name);
        console.log('- Tool:', step.tool_name);
      },
      onStepFinish: (step) => {
        stepFinishCount++;
        console.log(`\n[onStepFinish #${stepFinishCount}]`);
        console.log('- Type:', step.type);
        console.log('- Result:', step.result ? JSON.stringify(step.result).substring(0, 100) : 'none');
      },
      onMessage: (message) => {
        messageCount++;
        console.log(`\n[onMessage #${messageCount}]`);
        console.log('- Content:', message.content?.substring(0, 100));
        console.log('- Tool calls:', message.tool_calls?.length || 0);
      }
    });
    
    console.log('\n✅ Test completed!');
    console.log(`- onStepStart called: ${stepStartCount} times`);
    console.log(`- onStepFinish called: ${stepFinishCount} times`);
    console.log(`- onMessage called: ${messageCount} times`);
    
    if (stepStartCount === 0 && stepFinishCount === 0 && messageCount === 0) {
      console.log('\n⚠️  WARNING: No callbacks were triggered!');
      console.log('This might indicate the SDK version doesn\'t support these callbacks.');
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

// Run the test
testCallbacks();