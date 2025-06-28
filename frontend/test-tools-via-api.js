#!/usr/bin/env node

console.log('🧪 EspressoBot Tool Testing via API\n');
console.log('===================================\n');

console.log('⚠️  IMPORTANT: The multi-agent system has been updated!\n');
console.log('To use the enhanced multi-agent orchestrator:');
console.log('1. Stop the current server (Ctrl+C)');
console.log('2. Start it again with: npm run dev');
console.log('3. The server will now use the Enhanced Multi-Agent Orchestrator');
console.log('   with all 10 specialized agents\n');

console.log('You should see in the server logs:');
console.log('   "Using Multi-Agent Orchestrator"\n');

console.log('Press Enter when the server is running...');

// Wait for user input
process.stdin.once('data', async () => {
  await runTests();
});

async function runTests() {
  const API_BASE = 'http://localhost:5173';
  const AGENT_ENDPOINT = `${API_BASE}/api/agent/run`;
  
  // Test scenarios
  const testScenarios = [
    {
      category: "🔍 Product Search Tools",
      tests: [
        {
          name: "search_products",
          message: "Search for active coffee grinders under $500",
          validate: (response) => response.includes('product') || response.includes('found')
        },
        {
          name: "get_product", 
          message: "Get full details for the product with SKU 'Urnex-Grindz-15oz'",
          validate: (response) => response.includes('Urnex') || response.includes('Grindz')
        }
      ]
    },
    {
      category: "🆕 Product Creation Tools",
      tests: [
        {
          name: "create_product",
          message: "Create a test product called 'API Test Coffee Grinder 2024' with price $299.99, SKU TEST-API-GRINDER-2024, and set it to draft status",
          validate: (response) => response.includes('created') || response.includes('successfully')
        },
        {
          name: "create_combo",
          message: "Create a test combo product bundling SKUs 'TEST-API-GRINDER-2024' and 'Urnex-Grindz-15oz' called 'Test Grinder Bundle API' with a 10% discount off the combined price",
          validate: (response) => response.includes('combo') || response.includes('bundle') || response.includes('created')
        }
      ]
    },
    {
      category: "✏️ Product Update Tools", 
      tests: [
        {
          name: "update_pricing",
          message: "Update the price of product with SKU TEST-API-GRINDER-2024 to $279.99",
          validate: (response) => response.includes('updated') || response.includes('price')
        },
        {
          name: "manage_tags",
          message: "Add tags 'api-test', 'demo-product', and '2024' to the product with SKU TEST-API-GRINDER-2024",
          validate: (response) => response.includes('tag') || response.includes('added')
        },
        {
          name: "update_status",
          message: "Change the status of product SKU TEST-API-GRINDER-2024 to active",
          validate: (response) => response.includes('status') || response.includes('active')
        }
      ]
    },
    {
      category: "📦 Inventory Tools",
      tests: [
        {
          name: "manage_inventory_policy",
          message: "Set inventory tracking policy to 'track' for product SKU TEST-API-GRINDER-2024",
          validate: (response) => response.includes('inventory') || response.includes('policy') || response.includes('track')
        }
      ]
    },
    {
      category: "🧹 Cleanup",
      tests: [
        {
          name: "cleanup_status",
          message: "Set the status of products with SKUs TEST-API-GRINDER-2024 and the combo bundle to archived",
          validate: (response) => response.includes('archived') || response.includes('status')
        }
      ]
    }
  ];

  let conversationId = null;
  
  for (const category of testScenarios) {
    console.log(`\n${category.category}\n`);
    
    for (const test of category.tests) {
      console.log(`\n📋 Testing: ${test.name}`);
      console.log(`   Query: "${test.message}"`);
      
      try {
        const startTime = Date.now();
        const response = await fetch(AGENT_ENDPOINT, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            message: test.message,
            conv_id: conversationId 
          })
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        
        // Read SSE stream
        const text = await response.text();
        const lines = text.split('\n');
        
        let finalResponse = '';
        let agents = new Set();
        let tools = new Set();
        
        for (const line of lines) {
          if (line.startsWith('event: conversation_id')) {
            const dataLine = lines[lines.indexOf(line) + 1];
            if (dataLine && dataLine.startsWith('data: ')) {
              const data = JSON.parse(dataLine.substring(6));
              conversationId = data.conv_id;
            }
          } else if (line.startsWith('event: agent_processing')) {
            const dataLine = lines[lines.indexOf(line) + 1];
            if (dataLine && dataLine.startsWith('data: ')) {
              const data = JSON.parse(dataLine.substring(6));
              if (data.agent) agents.add(data.agent);
            }
          } else if (line.startsWith('event: tool_call')) {
            const dataLine = lines[lines.indexOf(line) + 1];
            if (dataLine && dataLine.startsWith('data: ')) {
              const data = JSON.parse(dataLine.substring(6));
              if (data.tool) tools.add(data.tool);
            }
          } else if (line.startsWith('event: done')) {
            const dataLine = lines[lines.indexOf(line) + 1];
            if (dataLine && dataLine.startsWith('data: ')) {
              const data = JSON.parse(dataLine.substring(6));
              finalResponse = data.finalResponse || '';
            }
          }
        }
        
        const duration = Date.now() - startTime;
        const agentsUsed = Array.from(agents).join(', ');
        const toolsUsed = Array.from(tools).join(', ');
        
        console.log(`   ⏱️  Duration: ${(duration/1000).toFixed(1)}s`);
        console.log(`   🤖 Agents: ${agentsUsed || 'None detected'}`);
        console.log(`   🔧 Tools: ${toolsUsed || 'None detected'}`);
        
        const isValid = test.validate(finalResponse);
        console.log(`   ✓ Response valid: ${isValid ? '✅' : '❌'}`);
        
        if (finalResponse) {
          console.log(`   📝 Response: ${finalResponse.substring(0, 200)}${finalResponse.length > 200 ? '...' : ''}`);
        }
        
      } catch (error) {
        console.error(`   ❌ Error: ${error.message}`);
      }
      
      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  console.log('\n\n✅ All tests completed!\n');
  process.exit(0);
}

// Polyfill for fetch if needed
if (typeof fetch === 'undefined') {
  global.fetch = (await import('node-fetch')).default;
}