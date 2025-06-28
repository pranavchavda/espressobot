#!/usr/bin/env node

import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import enhancedOrchestrator from './server/enhanced-multi-agent-orchestrator-v2.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('🧪 Detailed Tracing Test\n');

// Create a detailed tracing exporter
class DetailedTracingExporter {
  export(trace) {
    console.log('\n📊 FULL TRACE:');
    console.log('Trace ID:', trace.trace_id);
    console.log('Workflow:', trace.workflow_name);
    
    if (trace.steps && trace.steps.length > 0) {
      console.log(`\nSteps (${trace.steps.length}):`);
      trace.steps.forEach((step, i) => {
        console.log(`\n  Step ${i + 1}:`);
        console.log(`    Type: ${step.type}`);
        console.log(`    Agent: ${step.agent_name || 'N/A'}`);
        
        if (step.type === 'handoff') {
          console.log(`    Handoff to: ${step.handoff_to || 'N/A'}`);
        }
        
        if (step.tool_calls && step.tool_calls.length > 0) {
          console.log(`    Tool calls:`);
          step.tool_calls.forEach(tc => {
            console.log(`      - ${tc.tool_name}`);
          });
        }
        
        if (step.output) {
          console.log(`    Output: ${JSON.stringify(step.output).substring(0, 100)}...`);
        }
      });
    }
  }
}

const tracingExporter = new DetailedTracingExporter();

async function testQuery(query) {
  console.log(`\n🔍 Testing: "${query}"\n`);
  
  const stepLog = [];
  
  try {
    const result = await run(enhancedOrchestrator, query, {
      maxTurns: 10,
      tracingExporter: tracingExporter,
      onStepStart: (step) => {
        const logEntry = {
          event: 'start',
          type: step.type,
          agent: step.agent?.name,
          handoff_to: step.handoff_to,
          tool: step.tool_name
        };
        stepLog.push(logEntry);
        console.log('▶️  Step Start:', logEntry);
      },
      onStepFinish: (step, output) => {
        const logEntry = {
          event: 'finish',
          type: step.type,
          hasOutput: !!output
        };
        stepLog.push(logEntry);
        console.log('⏹️  Step Finish:', logEntry);
      }
    });
    
    console.log('\n📋 Step Summary:');
    const handoffs = stepLog.filter(s => s.type === 'handoff');
    const toolCalls = stepLog.filter(s => s.type === 'tool_call');
    
    console.log(`  Handoffs: ${handoffs.length}`);
    handoffs.forEach(h => {
      console.log(`    - ${h.agent} → ${h.handoff_to}`);
    });
    
    console.log(`  Tool calls: ${toolCalls.length}`);
    toolCalls.forEach(t => {
      console.log(`    - ${t.agent}: ${t.tool}`);
    });
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

// Run tests
async function main() {
  // Test different queries
  await testQuery("Search for coffee grinders under $1000");
  await testQuery("Create a test product called Demo Coffee Maker");
  
  // Check if catalog query agent has tools
  console.log('\n🔧 Agent Tool Check:');
  const catalogAgent = enhancedOrchestrator.handoffs.find(h => h.name === 'Catalog_Query_Agent');
  console.log('Catalog Query Agent tools:', catalogAgent?.tools?.length || 0);
  console.log('Tool names:', catalogAgent?.tools?.map(t => t.name || 'string tool') || []);
}

main();