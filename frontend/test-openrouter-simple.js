#!/usr/bin/env node
/**
 * Simple OpenRouter test with low token limits
 */

import { OpenRouterProvider } from './server/models/openrouter-provider.js';
import { Agent, run } from '@openai/agents';
import dotenv from 'dotenv';

dotenv.config();

async function simpleTest() {
  console.log('🧪 Simple OpenRouter test...\n');

  try {
    const provider = new OpenRouterProvider({
      apiKey: process.env.OPENROUTER_API_KEY,
      defaultModel: 'openai/gpt-3.5-turbo' // Cheapest model
    });

    const agent = new Agent({
      name: 'Simple Test',
      instructions: 'You are helpful. Keep responses under 50 words.',
      model: provider.getModel()
    });

    const result = await run(agent, 'Say hello in 5 words', {
      maxTurns: 1,
      stream: false
    });

    if (result?.output?.length > 0) {
      console.log('✅ SUCCESS!');
      console.log('Response:', result.output[0]?.content?.[0]?.text);
    } else {
      console.log('❌ No output received');
    }

  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

simpleTest();