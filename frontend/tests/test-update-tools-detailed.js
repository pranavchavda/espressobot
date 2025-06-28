#!/usr/bin/env node

console.log('🔍 Detailed Update Tools Test\n');

const fetch = (await import('node-fetch')).default;

async function detailedTest(message) {
  console.log(`\nQuery: "${message}"`);
  
  const response = await fetch('http://localhost:5173/api/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const text = await response.text();
  const lines = text.split('\n');
  
  let agent = null;
  let toolCalled = null;
  let error = null;
  
  // Parse events
  for (let i = 0; i < lines.length; i++) {
    if (lines[i] === 'event: agent_message' && lines[i+1]?.startsWith('data: ')) {
      const data = JSON.parse(lines[i+1].substring(6));
      agent = data.agent;
    }
    
    if (lines[i] === 'event: tool_call' && lines[i+1]?.startsWith('data: ')) {
      const data = JSON.parse(lines[i+1].substring(6));
      toolCalled = data.tool;
      console.log(`Tool: ${data.tool}`);
      console.log('Args:', JSON.stringify(data.args, null, 2));
    }
    
    if (lines[i] === 'event: error' && lines[i+1]?.startsWith('data: ')) {
      const data = JSON.parse(lines[i+1].substring(6));
      error = data.message;
    }
    
    if (lines[i] === 'event: done' && lines[i+1]?.startsWith('data: ')) {
      const data = JSON.parse(lines[i+1].substring(6));
      const response = data.finalResponse || '';
      
      console.log(`Agent: ${agent || 'Unknown'}`);
      if (error) {
        console.log(`Error: ${error}`);
      }
      console.log('Result:', response.substring(0, 200) + (response.length > 200 ? '...' : ''));
    }
  }
}

// Test each update tool
console.log('=== Update Pricing Tool ===');
await detailedTest("Use update_pricing tool to set price of SKU UPDATE-TEST-001 to $85.00");

console.log('\n=== Manage Tags Tool ===');
await detailedTest("Use manage_tags tool to add tags 'sale,featured' to product UPDATE-TEST-001");

console.log('\n=== Update Status Tool ===');
await detailedTest("Use update_product_status tool to set status ACTIVE for product UPDATE-TEST-001");

console.log('\n=== Direct Tool Parameters ===');
await detailedTest("Call update_pricing with identifier='UPDATE-TEST-001' and price='75.00'");

console.log('\n✅ Detailed tests completed!');