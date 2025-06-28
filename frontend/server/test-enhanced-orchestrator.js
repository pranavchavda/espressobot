import { Agent, run, handoff } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { openAITools } from './tools/openai-tool-converter.js';
import logger from './logger.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('🔧 Testing Enhanced Multi-Agent Orchestrator...\n');

// Initialize tools
console.log('📦 Initializing OpenAI-compatible tools...');
console.log(`✅ Loaded ${Object.keys(openAITools).length} tools\n`);

console.log('📋 Available tools:');
Object.keys(openAITools).forEach(name => {
  console.log(`   - ${name}`);
});

// Import specialized agents
const agents = {};
try {
  agents.catalogQuery = (await import('./agents/specialized/catalog_query_agent.js')).default;
  agents.channelSpecials = (await import('./agents/specialized/channel_specials_agent.js')).default;
  agents.inventory = (await import('./agents/specialized/inventory_agent.js')).default;
  agents.productCreation = (await import('./agents/specialized/product_creation_agent.js')).default;
  agents.productUpdate = (await import('./agents/specialized/product_update_agent.js')).default;
  agents.secureData = (await import('./agents/specialized/secure_data_agent.js')).default;
  agents.systemHealth = (await import('./agents/specialized/system_health_agent.js')).default;
  agents.taskPlanning = (await import('./agents/specialized/task_planning_agent.js')).default;
  agents.userClarification = (await import('./agents/specialized/user_clarification_agent.js')).default;
  
  console.log('\n✅ Imported all specialized agents');
} catch (error) {
  console.error('❌ Error importing agents:', error);
  process.exit(1);
}

// Now replace string tool names with actual OpenAI tool objects
console.log('\n🔄 Replacing string tool names with OpenAI tool objects...');
Object.entries(agents).forEach(([agentName, agent]) => {
  if (agent.tools && Array.isArray(agent.tools)) {
    const newTools = [];
    agent.tools.forEach(toolName => {
      if (typeof toolName === 'string') {
        const tool = openAITools[toolName];
        if (tool) {
          newTools.push(tool);
          console.log(`   ✅ ${agentName}: mapped "${toolName}" to OpenAI tool`);
        } else {
          console.warn(`   ⚠️  ${agentName}: tool "${toolName}" not found`);
        }
      } else {
        // Keep non-string tools (like handoffs)
        newTools.push(toolName);
      }
    });
    agent.tools = newTools;
  }
});

// Create a simple orchestrator for testing
const testOrchestrator = new Agent({
  name: 'Test_Orchestrator',
  description: 'Test orchestrator for verifying agent integration',
  instructions: `You are a test orchestrator. Route requests to the appropriate specialized agent:
- Catalog_Query_Agent: for product searches
- Product_Creation_Agent: for creating products
- Product_Update_Agent: for updating products
- System_Health_Agent: for health checks
Choose the right agent based on the user's request.`,
  tools: [
    handoff(agents.catalogQuery, "Hand off to catalog query agent"),
    handoff(agents.productCreation, "Hand off to product creation agent"),
    handoff(agents.productUpdate, "Hand off to product update agent"),
    handoff(agents.systemHealth, "Hand off to system health agent")
  ],
  model: 'gpt-4-turbo-preview'
});

// Add handoffs back to orchestrator
const handoffToOrchestrator = handoff(testOrchestrator, "Return to orchestrator");
Object.values(agents).forEach(agent => {
  if (agent.tools) {
    agent.tools.push(handoffToOrchestrator);
  } else {
    agent.tools = [handoffToOrchestrator];
  }
});

console.log('\n✅ Added bidirectional handoffs to all agents');

// Test cases
const testCases = [
  {
    name: "System Health Check",
    query: "Test the system connection",
    expectedAgent: "System_Health_Agent"
  }
];

// Run tests
console.log('\n\n🧪 Running test cases...\n');

for (const testCase of testCases) {
  console.log(`\n📋 Test: ${testCase.name}`);
  console.log(`   Query: "${testCase.query}"`);
  console.log(`   Expected: ${testCase.expectedAgent}`);
  
  try {
    const result = await run(testOrchestrator, testCase.query, {
      maxTurns: 3,
      onStepStart: (step) => {
        if (step.type === 'handoff') {
          console.log(`   ➡️  Handoff to: ${step.targetAgent?.name || 'unknown'}`);
        } else if (step.type === 'tool_call') {
          console.log(`   🔧 Tool call: ${step.tool?.name || step.tool_name}`);
        }
      },
      onStepFinish: (step, output) => {
        if (step.type === 'tool_call' && output) {
          console.log(`   ✅ Tool result: ${JSON.stringify(output).substring(0, 100)}...`);
        }
      }
    });
    
    // Extract response
    let response = 'No response';
    if (result?.state?._currentStep?.output) {
      response = result.state._currentStep.output;
    }
    
    console.log(`   📝 Response: ${response.substring(0, 200)}...`);
    
  } catch (error) {
    console.error(`   ❌ Error: ${error.message}`);
  }
}

console.log('\n\n✅ Enhanced orchestrator test complete!');
process.exit(0);