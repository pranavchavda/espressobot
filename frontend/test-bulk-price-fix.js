#!/usr/bin/env node

console.log('🔍 Testing bulk_price_update schema fix\n');

const fetch = (await import('node-fetch')).default;

async function testBulkPriceUpdate() {
  const message = "Update the price of products with SKUs TEST-001 and TEST-002 to $50.00 each";
  
  console.log(`Query: "${message}"\n`);
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    // Look for errors
    let foundError = false;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i] === 'event: error' && lines[i+1]?.startsWith('data: ')) {
        const data = JSON.parse(lines[i+1].substring(6));
        foundError = true;
        console.log('❌ Error:', data.message);
        if (data.message.includes('bulk_price_update') && data.message.includes('schema')) {
          console.log('\n⚠️  Schema error still present!');
          console.log('The bulk_price_update tool schema needs fixing.');
        }
      }
      
      if (lines[i] === 'event: done' && !foundError) {
        console.log('✅ Request completed without schema errors');
      }
    }
  } catch (error) {
    console.error('Request failed:', error.message);
  }
}

console.log('Testing bulk_price_update after schema fix...\n');
await testBulkPriceUpdate();
console.log('\n✅ Test completed!');