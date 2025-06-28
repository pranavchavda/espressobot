import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { openAITools } from './tools/openai-tool-converter.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('🧪 Simple Agent Test\n');

// Import just one agent to test
import catalogQueryAgent from './agents/specialized/catalog_query_agent.js';

// Assign tools to the agent
const toolsToAssign = ['search_products', 'get_product'];
catalogQueryAgent.tools = toolsToAssign.map(name => openAITools[name]).filter(t => t);

console.log(`✅ Configured ${catalogQueryAgent.name} with ${catalogQueryAgent.tools.length} tools\n`);

// Test the agent directly
const testQuery = "Search for coffee products under $300";
console.log(`📋 Query: "${testQuery}"\n`);

try {
  const result = await run(catalogQueryAgent, testQuery, {
    maxTurns: 3,
    onStepStart: (step) => {
      if (step.type === 'tool_call') {
        const toolName = step.tool?.name || step.tool_name || 'Unknown';
        console.log(`🔧 Calling tool: ${toolName}`);
      }
    },
    onStepFinish: (step, output) => {
      if (step.type === 'tool_call' && output) {
        const outputStr = typeof output === 'string' ? output : JSON.stringify(output);
        console.log(`   Result: ${outputStr.substring(0, 200)}...`);
      }
    }
  });
  
  // Extract response
  let response = 'No response';
  if (result?.state?._currentStep?.output) {
    response = result.state._currentStep.output;
  }
  
  console.log(`\n📝 Response: ${response}\n`);
  console.log('✅ Test completed successfully!');
  
} catch (error) {
  console.error('\n❌ Error:', error.message);
  console.error('Stack:', error.stack);
}

process.exit(0);