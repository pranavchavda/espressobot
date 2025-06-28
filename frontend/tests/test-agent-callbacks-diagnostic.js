#!/usr/bin/env node

import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { tool } from '@openai/agents';
import { z } from 'zod';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Simple test tool
const testTool = tool({
  name: 'simple_test',
  description: 'A simple test tool',
  parameters: z.object({
    message: z.string()
  }),
  execute: async ({ message }) => {
    console.log('[TOOL EXECUTE] Message:', message);
    return `Tool executed with: ${message}`;
  }
});

// Create test agents with different configurations
const agents = [
  {
    name: 'Simple Agent (no tools)',
    agent: new Agent({
      name: 'Simple_Agent',
      instructions: 'You are a simple test agent. Just respond with "Hello!"',
      model: 'gpt-4.1-mini'
    }),
    prompt: 'Say hello'
  },
  {
    name: 'Tool Agent',
    agent: new Agent({
      name: 'Tool_Agent', 
      instructions: 'You are a test agent. Use the simple_test tool with message "testing callbacks"',
      model: 'gpt-4.1-mini',
      tools: [testTool]
    }),
    prompt: 'Please test the tool'
  }
];

async function testAgentCallbacks() {
  console.log('🧪 Testing OpenAI Agents SDK Callbacks - Diagnostic\n');
  console.log('SDK Version Check:');
  console.log('- @openai/agents imported:', typeof Agent === 'function' ? '✓' : '✗');
  console.log('- run function imported:', typeof run === 'function' ? '✓' : '✗');
  console.log();
  
  for (const testCase of agents) {
    console.log(`\n=== Testing: ${testCase.name} ===`);
    
    let callbacksFired = {
      onMessage: 0,
      onStepStart: 0,
      onStepFinish: 0
    };
    
    try {
      const result = await run(testCase.agent, testCase.prompt, {
        maxTurns: 1,
        onMessage: (message) => {
          callbacksFired.onMessage++;
          console.log('✅ onMessage fired');
          console.log('  - Type:', typeof message);
          console.log('  - Has content:', !!message?.content);
          console.log('  - Has tool_calls:', !!message?.tool_calls);
        },
        onStepStart: (step) => {
          callbacksFired.onStepStart++;
          console.log('✅ onStepStart fired');
          console.log('  - Step type:', step.type);
        },
        onStepFinish: (step) => {
          callbacksFired.onStepFinish++;
          console.log('✅ onStepFinish fired');
          console.log('  - Step type:', step.type);
        }
      });
      
      console.log('\nResult:', result.finalOutput || 'No output');
      console.log('\nCallback Summary:');
      console.log(`- onMessage: ${callbacksFired.onMessage} times`);
      console.log(`- onStepStart: ${callbacksFired.onStepStart} times`);
      console.log(`- onStepFinish: ${callbacksFired.onStepFinish} times`);
      
      if (Object.values(callbacksFired).every(count => count === 0)) {
        console.log('\n⚠️  WARNING: No callbacks were triggered!');
      }
      
    } catch (error) {
      console.error('❌ Error:', error.message);
    }
  }
  
  console.log('\n\n=== Diagnostic Complete ===');
  console.log('If no callbacks fired, possible issues:');
  console.log('1. SDK version may not support these callbacks');
  console.log('2. Callbacks might have different names or signatures');
  console.log('3. Agent configuration might need adjustment');
}

// Run the diagnostic
testAgentCallbacks();