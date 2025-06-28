import fetch from 'node-fetch';
import EventSource from 'eventsource';

console.log('🧪 EspressoBot Agency API Test Client\n');
console.log('=====================================\n');

const API_BASE = 'http://localhost:5173';
const AGENT_ENDPOINT = `${API_BASE}/api/agent/run`;

// Test scenarios for different tools
const testScenarios = [
  {
    category: "Product Search Tools",
    tests: [
      {
        name: "Test search_products",
        message: "Search for active coffee products under $500",
        expectedAgent: "Catalog_Query_Agent",
        expectedTools: ["search_products"]
      },
      {
        name: "Test get_product",
        message: "Get details for product with SKU 'Urnex-Grindz-15oz'",
        expectedAgent: "Catalog_Query_Agent",
        expectedTools: ["get_product"]
      }
    ]
  },
  {
    category: "Product Creation Tools",
    tests: [
      {
        name: "Test create_product",
        message: "Create a test product called 'Test Coffee Grinder 2024' with price $299.99 and SKU TEST-GRINDER-2024",
        expectedAgent: "Product_Creation_Agent",
        expectedTools: ["create_product", "product_create_full"]
      },
      {
        name: "Test create_combo",
        message: "Create a combo product bundling SKUs 'TEST-GRINDER-2024' and 'Urnex-Grindz-15oz' called 'Grinder Cleaning Bundle' with 10% discount",
        expectedAgent: "Product_Creation_Agent",
        expectedTools: ["create_combo"]
      }
    ]
  },
  {
    category: "Product Update Tools",
    tests: [
      {
        name: "Test update_pricing",
        message: "Update the price of product SKU TEST-GRINDER-2024 to $279.99",
        expectedAgent: "Product_Update_Agent",
        expectedTools: ["search_products", "update_pricing"]
      },
      {
        name: "Test manage_tags",
        message: "Add tags 'test-product' and 'demo' to product SKU TEST-GRINDER-2024",
        expectedAgent: "Product_Update_Agent",
        expectedTools: ["search_products", "manage_tags"]
      },
      {
        name: "Test update_status",
        message: "Set the status of product SKU TEST-GRINDER-2024 to draft",
        expectedAgent: "Product_Update_Agent",
        expectedTools: ["search_products", "update_status"]
      }
    ]
  },
  {
    category: "Inventory Tools",
    tests: [
      {
        name: "Test manage_inventory_policy",
        message: "Set inventory policy to 'track' for product SKU TEST-GRINDER-2024",
        expectedAgent: "Inventory_Agent",
        expectedTools: ["manage_inventory_policy"]
      }
    ]
  }
];

// Function to send request and handle SSE response
async function testAgentAPI(message, conversationId = null) {
  return new Promise(async (resolve, reject) => {
    const results = {
      agents: new Set(),
      tools: new Set(),
      responses: [],
      errors: [],
      conversationId: conversationId
    };

    try {
      // Prepare request body
      const requestBody = {
        message: message,
        conv_id: conversationId
      };

      // Make the request
      const response = await fetch(AGENT_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // The response is SSE, so we need to read it as a stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.substring(7);
            const nextLine = lines[lines.indexOf(line) + 1];
            if (nextLine && nextLine.startsWith('data: ')) {
              try {
                const data = JSON.parse(nextLine.substring(6));
                
                switch (eventType) {
                  case 'conversation_id':
                    results.conversationId = data.conv_id;
                    break;
                  case 'agent_processing':
                    if (data.agent) {
                      results.agents.add(data.agent);
                    }
                    break;
                  case 'handoff':
                    console.log(`   ➡️  Handoff: ${data.from} → ${data.to}`);
                    if (data.to) {
                      results.agents.add(data.to);
                    }
                    break;
                  case 'tool_call':
                    if (data.tool) {
                      results.tools.add(data.tool);
                      console.log(`   🔧 Tool: ${data.agent} uses ${data.tool}`);
                    }
                    break;
                  case 'tool_result':
                    if (data.result && typeof data.result === 'string' && data.result.includes('error')) {
                      console.log(`      ❌ Tool error: ${data.result.substring(0, 100)}...`);
                      results.errors.push(data.result);
                    } else {
                      console.log(`      ✅ Tool success`);
                    }
                    break;
                  case 'assistant_message':
                    results.responses.push(data.content || data);
                    break;
                  case 'error':
                    console.log(`   ❌ Error: ${data.message}`);
                    results.errors.push(data.message);
                    break;
                  case 'done':
                    reader.cancel();
                    resolve(results);
                    return;
                }
              } catch (e) {
                // Ignore parsing errors
              }
            }
          }
        }
      }

      resolve(results);
    } catch (error) {
      reject(error);
    }
  });
}

// Run tests
async function runTests() {
  let conversationId = null;

  for (const category of testScenarios) {
    console.log(`\n📂 ${category.category}\n`);
    
    for (const test of category.tests) {
      console.log(`\n📋 ${test.name}`);
      console.log(`   Query: "${test.message}"`);
      console.log(`   Expected: ${test.expectedAgent} using ${test.expectedTools.join(', ')}`);
      
      try {
        const results = await testAgentAPI(test.message, conversationId);
        
        // Extract conversation ID if provided
        if (results.conversationId) {
          conversationId = results.conversationId;
        }
        
        const agentsArray = Array.from(results.agents);
        const toolsArray = Array.from(results.tools);
        
        console.log(`\n   📊 Results:`);
        console.log(`      Agents: ${agentsArray.join(', ') || 'None'}`);
        console.log(`      Tools: ${toolsArray.join(', ') || 'None'}`);
        console.log(`      Errors: ${results.errors.length}`);
        
        // Show response
        if (results.responses.length > 0) {
          const response = results.responses[results.responses.length - 1];
          console.log(`\n   📝 Response: ${response.substring(0, 200)}${response.length > 200 ? '...' : ''}`);
        }
        
        // Verify expectations
        const correctAgent = agentsArray.includes(test.expectedAgent);
        const correctTools = test.expectedTools.every(tool => toolsArray.includes(tool));
        
        console.log(`\n   ✓ Expected agent: ${correctAgent ? '✅' : '❌'}`);
        console.log(`   ✓ Expected tools: ${correctTools ? '✅' : '❌'}`);
        
      } catch (error) {
        console.error(`\n   ❌ Test failed: ${error.message}`);
      }
      
      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  }
  
  console.log('\n\n✅ All tests completed!');
}

// Check if server is running
console.log('🔍 Checking if server is running...');
fetch(`${API_BASE}/api/conversations/user/1`)
  .then(response => {
    if (response.ok) {
      console.log('✅ Server is running!\n');
      console.log('⚠️  Note: Make sure USE_MULTI_AGENT=true is set in your .env file\n');
      console.log('Starting tests in 3 seconds...\n');
      setTimeout(runTests, 3000);
    } else {
      throw new Error('Server returned error');
    }
  })
  .catch(error => {
    console.error('❌ Server is not running or not accessible');
    console.error('Please start the server with: npm run dev');
    process.exit(1);
  });