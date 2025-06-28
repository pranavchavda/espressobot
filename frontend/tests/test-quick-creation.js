#!/usr/bin/env node

console.log('🚀 Quick Product Creation Test\n');

const fetch = (await import('node-fetch')).default;

async function quickTest(message) {
  console.log(`Testing: "${message}"`);
  
  const response = await fetch('http://localhost:5173/api/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const text = await response.text();
  const lines = text.split('\n');
  
  // Look for success indicators
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i] === 'event: done' && lines[i+1]?.startsWith('data: ')) {
      const data = JSON.parse(lines[i+1].substring(6));
      const response = data.finalResponse || '';
      
      if (response.includes('successfully created') || response.includes('gid://')) {
        console.log('✅ Success!');
        // Extract product ID if available
        const idMatch = response.match(/gid:\/\/shopify\/Product\/(\d+)/);
        if (idMatch) {
          console.log('   Product ID:', idMatch[0]);
        }
      } else {
        console.log('Response:', response.substring(0, 150) + '...');
      }
      break;
    }
  }
  console.log();
}

// Run tests
await quickTest("Create product 'QUICK TEST 1' vendor 'Test' type 'Equipment' price $50");
await quickTest("Create product 'QUICK TEST 2' with SKU QUICK-002, vendor 'TestCo', type 'Machines', 25 units in stock");
await quickTest("Search for products with title:QUICK*");

console.log('✅ Quick tests completed!');