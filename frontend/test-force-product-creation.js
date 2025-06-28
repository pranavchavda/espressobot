#!/usr/bin/env node

console.log('🧪 Force Product Creation Test\n');

const fetch = (await import('node-fetch')).default;

async function forceProductCreation() {
  // Try multiple approaches to trigger product creation
  const tests = [
    {
      name: "Direct agent request",
      message: "Product_Creation_Agent, please create a product with title 'FORCE TEST 1', vendor 'Test', and product_type 'Equipment'"
    },
    {
      name: "Explicit tool request",
      message: "I need you to use the create_product tool with these parameters: title='FORCE TEST 2', vendor='Test Vendor', product_type='Test Equipment'"
    },
    {
      name: "Simple natural language",
      message: "Create a new product called FORCE TEST 3 from vendor Test Company as type Testing Equipment"
    },
    {
      name: "Task-oriented request",
      message: "Task: Create a product. Details: Title is FORCE TEST 4, vendor is TestCo, product type is Machines"
    }
  ];
  
  for (const test of tests) {
    console.log(`\n=== ${test.name} ===`);
    console.log(`Query: "${test.message}"`);
    
    try {
      const response = await fetch('http://localhost:5173/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: test.message })
      });
      
      const text = await response.text();
      const lines = text.split('\n');
      
      let foundToolCall = false;
      let foundError = false;
      let agentUsed = null;
      
      // Parse events
      for (let i = 0; i < lines.length; i++) {
        if (lines[i] === 'event: agent_message' && lines[i+1]?.startsWith('data: ')) {
          const data = JSON.parse(lines[i+1].substring(6));
          agentUsed = data.agent;
        }
        
        if (lines[i] === 'event: tool_call' && lines[i+1]?.startsWith('data: ')) {
          const data = JSON.parse(lines[i+1].substring(6));
          foundToolCall = true;
          console.log(`✅ Tool called: ${data.tool} by ${data.agent}`);
          console.log('   Args:', JSON.stringify(data.args, null, 2));
        }
        
        if (lines[i] === 'event: error' && lines[i+1]?.startsWith('data: ')) {
          const data = JSON.parse(lines[i+1].substring(6));
          foundError = true;
          console.log(`❌ Error: ${data.message}`);
        }
        
        if (lines[i] === 'event: done' && lines[i+1]?.startsWith('data: ')) {
          const data = JSON.parse(lines[i+1].substring(6));
          const response = data.finalResponse || '';
          
          if (!foundToolCall && !foundError) {
            if (agentUsed) {
              console.log(`Agent used: ${agentUsed}`);
            }
            
            // Check response content
            if (response.includes('created') || response.includes('gid://')) {
              console.log('✅ Product appears to be created');
            } else if (response.includes('error') || response.includes('failed')) {
              console.log('❌ Creation failed');
              console.log('Response:', response.substring(0, 200));
            } else {
              console.log('❓ Unclear result');
              console.log('Response preview:', response.substring(0, 150) + '...');
            }
          }
        }
      }
      
    } catch (error) {
      console.log('Request error:', error.message);
    }
    
    // Small delay between tests
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
}

console.log('Starting forced product creation tests...\n');
await forceProductCreation();
console.log('\n✅ Tests completed!');