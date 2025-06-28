import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import enhancedOrchestrator from './enhanced-multi-agent-orchestrator-v2.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

console.log('🧪 Multi-Agent Integration Test\n');
console.log('================================\n');

// Test scenarios
const testScenarios = [
  {
    name: "Product Search",
    query: "Search for active coffee products under $500",
    expectedAgent: "Catalog_Query_Agent",
    expectedTools: ["search_products"]
  },
  {
    name: "Product Creation", 
    query: "Create a new combo product for two coffee machines bundled together",
    expectedAgent: "Product_Creation_Agent",
    expectedTools: ["create_combo"]
  },
  {
    name: "Price Update",
    query: "Update the price of product with SKU TEST123 to $199.99",
    expectedAgent: "Product_Update_Agent",
    expectedTools: ["search_products", "update_pricing"]
  },
  {
    name: "Inventory Management",
    query: "Set inventory policy to track for products with SKU TEST456",
    expectedAgent: "Inventory_Agent",
    expectedTools: ["manage_inventory_policy"]
  },
  {
    name: "Complex Task",
    query: "I need to create a sale on all coffee grinders, reducing prices by 20% and adding a 'SALE' tag",
    expectedAgent: "Task_Planning_Agent",
    expectedTools: []
  }
];

// Run tests
for (const scenario of testScenarios) {
  console.log(`\n📋 Scenario: ${scenario.name}`);
  console.log(`   Query: "${scenario.query}"`);
  console.log(`   Expected Agent: ${scenario.expectedAgent}`);
  console.log(`   Expected Tools: ${scenario.expectedTools.join(', ') || 'None'}`);
  
  const agentsUsed = new Set();
  const toolsUsed = new Set();
  let currentAgent = 'Enhanced_EspressoBot_Orchestrator';
  
  try {
    const result = await run(enhancedOrchestrator, scenario.query, {
      maxTurns: 10,
      onStepStart: (step) => {
        if (step.agent?.name) {
          currentAgent = step.agent.name;
          agentsUsed.add(currentAgent);
        }
        
        if (step.type === 'handoff') {
          console.log(`   ➡️  Handoff: ${currentAgent} → ${step.handoff_to || 'Unknown'}`);
        } else if (step.type === 'tool_call') {
          const toolName = step.tool?.name || step.tool_name || 'Unknown';
          toolsUsed.add(toolName);
          console.log(`   🔧 Tool: ${currentAgent} uses ${toolName}`);
        }
      },
      onStepFinish: (step, output) => {
        if (step.type === 'tool_call' && output) {
          const outputStr = typeof output === 'string' ? output : JSON.stringify(output);
          if (outputStr.includes('error')) {
            console.log(`      ❌ Error: ${outputStr.substring(0, 100)}...`);
          } else {
            console.log(`      ✅ Success`);
          }
        }
      }
    });
    
    // Extract response
    let response = 'No response';
    if (result?.state?._currentStep?.output) {
      response = result.state._currentStep.output;
    }
    
    console.log(`\n   📝 Response: ${response.substring(0, 200)}${response.length > 200 ? '...' : ''}`);
    
    // Verify expectations
    const agentsArray = Array.from(agentsUsed);
    const toolsArray = Array.from(toolsUsed);
    
    console.log(`\n   📊 Results:`);
    console.log(`      Agents used: ${agentsArray.join(', ')}`);
    console.log(`      Tools used: ${toolsArray.join(', ') || 'None'}`);
    
    const correctAgent = agentsArray.includes(scenario.expectedAgent);
    console.log(`      Expected agent reached: ${correctAgent ? '✅' : '❌'}`);
    
  } catch (error) {
    console.error(`\n   ❌ Error: ${error.message}`);
  }
}

console.log('\n\n✅ Integration test complete!');
process.exit(0);