#!/usr/bin/env node

console.log('🔧 Product Update Tools Test\n');

const fetch = (await import('node-fetch')).default;

async function testUpdate(message) {
  console.log(`Testing: "${message}"`);
  
  const response = await fetch('http://localhost:5173/api/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const text = await response.text();
  const lines = text.split('\n');
  
  // Extract result
  for (let i = lines.length - 1; i >= 0; i--) {
    if (lines[i] === 'event: done' && lines[i+1]?.startsWith('data: ')) {
      const data = JSON.parse(lines[i+1].substring(6));
      const response = data.finalResponse || '';
      
      if (response.includes('successfully') || response.includes('updated') || response.includes('✅')) {
        console.log('✅ Success');
      } else if (response.includes('error') || response.includes('failed')) {
        console.log('❌ Failed:', response.substring(0, 150));
      } else {
        console.log('Response:', response.substring(0, 150) + '...');
      }
      break;
    }
  }
  console.log();
}

// First create a test product to update
console.log('=== Creating test product ===');
await testUpdate("Create product 'UPDATE TEST PRODUCT' vendor 'Test' type 'Equipment' price $100 SKU UPDATE-TEST-001");

console.log('\n=== Testing Update Tools ===\n');

// Test pricing update
await testUpdate("Update the price of product with SKU UPDATE-TEST-001 to $89.99");

// Test tag management
await testUpdate("Add tags 'test', 'updated', 'api' to product UPDATE-TEST-001");
await testUpdate("Remove tag 'test' from product UPDATE-TEST-001");

// Test status update
await testUpdate("Change status of product UPDATE-TEST-001 to ACTIVE");

// Test bulk pricing
await testUpdate("Update prices for products with SKUs UPDATE-TEST-001 setting price to $79.99");

// Test inventory policy
await testUpdate("Set inventory policy to CONTINUE for product UPDATE-TEST-001");

console.log('✅ Update tests completed!');