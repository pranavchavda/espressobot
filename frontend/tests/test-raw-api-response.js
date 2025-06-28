#!/usr/bin/env node

console.log('🔍 Raw API Response Test\n');

const fetch = (await import('node-fetch')).default;

async function captureRawResponse(message) {
  console.log(`Query: "${message}"\n`);
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    // Look for specific events
    console.log('Raw Events:');
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      // Print all events and their data
      if (line.startsWith('event: ')) {
        console.log(`\n${line}`);
        if (lines[i+1]?.startsWith('data: ')) {
          try {
            const data = JSON.parse(lines[i+1].substring(6));
            
            // Special handling for different event types
            if (line === 'event: tool_call') {
              console.log('Tool Call Details:');
              console.log('  Agent:', data.agent);
              console.log('  Tool:', data.tool);
              console.log('  Args:', JSON.stringify(data.args, null, 2));
            } else if (line === 'event: error') {
              console.log('Error Details:');
              console.log('  Message:', data.message);
              if (data.details) console.log('  Details:', data.details);
              if (data.stack) console.log('  Stack:', data.stack);
            } else if (line === 'event: done') {
              console.log('Final Response:', data.finalResponse?.substring(0, 200) + '...');
            } else {
              console.log('Data:', JSON.stringify(data).substring(0, 100) + '...');
            }
          } catch (e) {
            console.log('Raw data:', lines[i+1]);
          }
        }
      }
    }
    
  } catch (error) {
    console.error('Request Error:', error);
  }
}

// Test a simple product creation
console.log('=== Testing Simple Product Creation ===\n');
await captureRawResponse("Create a product with title 'RAW TEST 1', vendor 'Test', and product_type 'Equipment'");

console.log('\n\n=== Testing with Python Script Format ===\n');
await captureRawResponse("Run create_product.py with --title 'RAW TEST 2' --vendor 'Test' --type 'Equipment'");

console.log('\n✅ Test completed!');