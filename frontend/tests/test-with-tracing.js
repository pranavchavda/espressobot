#!/usr/bin/env node

import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import enhancedOrchestrator from './server/enhanced-multi-agent-orchestrator-v2.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('🧪 Testing with Tracing Enabled\n');

// Create a tracing exporter to capture all events
class ConsoleTracingExporter {
  export(trace) {
    console.log('\n📊 TRACE:', JSON.stringify(trace, null, 2));
  }
}

const tracingExporter = new ConsoleTracingExporter();

async function testWithTracing(query) {
  console.log(`\n💬 Query: "${query}"\n`);
  
  try {
    const result = await run(enhancedOrchestrator, query, {
      maxTurns: 5,
      tracingExporter: tracingExporter,
      onStepStart: (step) => {
        console.log('🔸 Step Start:', {
          type: step.type,
          agent: step.agent?.name,
          handoff_to: step.handoff_to,
          tool: step.tool_name,
          available_handoffs: step.agent?.handoffs?.map(h => h.name || 'unnamed')
        });
      },
      onStepFinish: (step, output) => {
        console.log('🔹 Step Finish:', {
          type: step.type,
          output: output ? 'Has output' : 'No output'
        });
      }
    });
    
    const response = result?.state?._currentStep?.output || 'No response';
    console.log(`\n📝 Response: ${response.substring(0, 200)}...\n`);
    
    // Log the final state
    console.log('🔍 Final State:', {
      currentAgent: result?.state?._currentAgent?.name,
      steps: result?.state?._steps?.length,
      handoffsAvailable: result?.state?._currentAgent?.handoffs?.length
    });
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error('Stack:', error.stack);
  }
}

// Test a simple query that should trigger a handoff
async function runTest() {
  await testWithTracing("Search for coffee grinders");
  
  // Also test the orchestrator's handoff configuration
  console.log('\n🔧 Orchestrator Configuration:');
  console.log('Name:', enhancedOrchestrator.name);
  console.log('Handoffs available:', enhancedOrchestrator.handoffs?.length || 0);
  console.log('Handoff names:', enhancedOrchestrator.handoffs?.map(h => h.name) || []);
}

runTest();