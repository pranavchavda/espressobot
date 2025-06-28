import { Agent, run, handoff } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { openAITools } from './tools/openai-tool-converter.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('🔧 Testing Enhanced Multi-Agent Orchestrator V2...\n');

// Initialize tools
console.log('📦 Initializing OpenAI-compatible tools...');
console.log(`✅ Loaded ${Object.keys(openAITools).length} tools\n`);

// Import specialized agents
const agents = {};
try {
  agents.catalogQuery = (await import('./agents/specialized/catalog_query_agent.js')).default;
  agents.systemHealth = (await import('./agents/specialized/system_health_agent.js')).default;
  agents.productUpdate = (await import('./agents/specialized/product_update_agent.js')).default;
  
  console.log('✅ Imported test agents\n');
} catch (error) {
  console.error('❌ Error importing agents:', error);
  process.exit(1);
}

// Replace string tool names with actual OpenAI tool objects
console.log('🔄 Configuring agent tools...');
Object.entries(agents).forEach(([agentName, agent]) => {
  if (agent.tools && Array.isArray(agent.tools)) {
    const newTools = [];
    agent.tools.forEach(toolName => {
      if (typeof toolName === 'string') {
        const tool = openAITools[toolName];
        if (tool) {
          newTools.push(tool);
          console.log(`   ✅ ${agentName}: added tool "${toolName}"`);
        } else {
          console.warn(`   ⚠️  ${agentName}: tool "${toolName}" not found`);
        }
      }
    });
    agent.tools = newTools;
  }
});

// Create test orchestrator with proper handoffs
const testOrchestrator = new Agent({
  name: 'Test_Orchestrator',
  description: 'Test orchestrator for verifying agent integration',
  instructions: `You are a test orchestrator. Route requests to the appropriate specialized agent:
- Catalog_Query_Agent: for product searches
- System_Health_Agent: for health checks and connection tests
- Product_Update_Agent: for updating products
Choose the right agent based on the user's request.`,
  model: 'gpt-4-turbo-preview',
  handoffs: [
    agents.catalogQuery,
    agents.systemHealth,
    agents.productUpdate
  ]
});

// Configure handoffs back to orchestrator
agents.catalogQuery.handoffs = [testOrchestrator];
agents.systemHealth.handoffs = [testOrchestrator];
agents.productUpdate.handoffs = [testOrchestrator];

console.log('✅ Configured bidirectional handoffs\n');

// Test a simple health check
console.log('\n🧪 Running test...\n');
console.log('Query: "Test the system connection"');

try {
  const result = await run(testOrchestrator, "Test the system connection", {
    maxTurns: 5,
    onStepStart: (step) => {
      if (step.type === 'handoff') {
        console.log(`\n➡️  Handoff: ${step.agent?.name || 'Unknown'} → ${step.handoff_to || 'Unknown'}`);
      } else if (step.type === 'tool_call') {
        console.log(`\n🔧 Tool call by ${step.agent?.name || 'Unknown'}: ${step.tool?.name || step.tool_name || 'Unknown'}`);
      }
    },
    onStepFinish: (step, output) => {
      if (step.type === 'tool_call' && output) {
        const outputStr = typeof output === 'string' ? output : JSON.stringify(output);
        console.log(`   Result: ${outputStr.substring(0, 100)}${outputStr.length > 100 ? '...' : ''}`);
      }
    }
  });
  
  // Extract response
  let response = 'No response';
  if (result?.state?._currentStep?.output) {
    response = result.state._currentStep.output;
  } else if (result?.messages?.length > 0) {
    const lastMessage = result.messages[result.messages.length - 1];
    response = lastMessage.content || 'No content';
  }
  
  console.log(`\n📝 Final Response: ${response}\n`);
  console.log('✅ Test completed successfully!');
  
} catch (error) {
  console.error('\n❌ Test failed:', error.message);
  console.error('Stack:', error.stack);
}

process.exit(0);