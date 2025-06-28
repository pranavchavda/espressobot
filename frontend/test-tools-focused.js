#!/usr/bin/env node

console.log('🧪 Focused Tool Testing via EspressoBot API\n');

const API_BASE = 'http://localhost:5173';
const AGENT_ENDPOINT = `${API_BASE}/api/agent/run`;

async function testTool(message, conversationId = null) {
  const fetch = (await import('node-fetch')).default;
  
  const response = await fetch(AGENT_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      message: message,
      conv_id: conversationId 
    })
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  const text = await response.text();
  const lines = text.split('\n');
  
  let finalResponse = '';
  const agents = new Set();
  const tools = new Set();
  let newConvId = conversationId;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('event: ')) {
      const eventType = line.substring(7);
      const dataLine = lines[i + 1];
      
      if (dataLine && dataLine.startsWith('data: ')) {
        try {
          const data = JSON.parse(dataLine.substring(6));
          
          switch (eventType) {
            case 'conversation_id':
              newConvId = data.conv_id;
              break;
            case 'agent_processing':
              if (data.agent) agents.add(data.agent);
              break;
            case 'handoff':
              if (data.to) agents.add(data.to);
              break;
            case 'tool_call':
              if (data.tool) tools.add(data.tool);
              break;
            case 'done':
              finalResponse = data.finalResponse || '';
              break;
          }
        } catch (e) {
          // Ignore JSON parse errors
        }
      }
    }
  }
  
  return {
    response: finalResponse,
    agents: Array.from(agents),
    tools: Array.from(tools),
    conversationId: newConvId
  };
}

async function runTests() {
  let conversationId = null;
  
  const tests = [
    {
      category: "🔍 Search Tools",
      items: [
        {
          name: "Basic product search",
          query: "Search for coffee grinders that are currently active",
          expectedTools: ["search_products"]
        },
        {
          name: "Get specific product",
          query: "Get details for the product with SKU 'Urnex-Grindz-15oz'",
          expectedTools: ["get_product"]
        }
      ]
    },
    {
      category: "🆕 Creation Tools",
      items: [
        {
          name: "Create test product",
          query: "Create a new product called 'Test Coffee Grinder API Demo' with price $299.99, SKU TEST-API-DEMO-001, vendor 'Test Vendor', product type 'Coffee Equipment', and set it to draft status",
          expectedTools: ["create_product", "product_create_full"]
        }
      ]
    },
    {
      category: "✏️ Update Tools",
      items: [
        {
          name: "Update pricing",
          query: "Find the product with SKU TEST-API-DEMO-001 and update its price to $279.99",
          expectedTools: ["search_products", "update_pricing"]
        },
        {
          name: "Add tags",
          query: "Add tags 'api-test', 'demo', and '2024' to the product with SKU TEST-API-DEMO-001",
          expectedTools: ["search_products", "manage_tags"]
        }
      ]
    },
    {
      category: "🧹 Cleanup",
      items: [
        {
          name: "Archive test product",
          query: "Change the status of product SKU TEST-API-DEMO-001 to archived",
          expectedTools: ["search_products", "update_status"]
        }
      ]
    }
  ];
  
  for (const category of tests) {
    console.log(`\n${category.category}\n`);
    
    for (const test of category.items) {
      console.log(`📋 ${test.name}`);
      console.log(`   Query: "${test.query}"`);
      
      try {
        const startTime = Date.now();
        const result = await testTool(test.query, conversationId);
        conversationId = result.conversationId;
        const duration = Date.now() - startTime;
        
        console.log(`   ⏱️  Time: ${(duration/1000).toFixed(1)}s`);
        console.log(`   🤖 Agents: ${result.agents.join(' → ')}`);
        console.log(`   🔧 Tools: ${result.tools.join(', ')}`);
        
        // Check if expected tools were used
        const expectedToolsUsed = test.expectedTools.filter(tool => 
          result.tools.includes(tool)
        );
        console.log(`   ✓ Expected tools used: ${expectedToolsUsed.length}/${test.expectedTools.length}`);
        
        // Show response preview
        if (result.response) {
          const preview = result.response.substring(0, 150);
          console.log(`   📝 Response: ${preview}${result.response.length > 150 ? '...' : ''}`);
        }
        
      } catch (error) {
        console.error(`   ❌ Error: ${error.message}`);
      }
      
      console.log('');
      
      // Small delay
      await new Promise(resolve => setTimeout(resolve, 1500));
    }
  }
  
  console.log('\n✅ Testing complete!\n');
}

runTests();