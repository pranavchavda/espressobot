#!/usr/bin/env node

const fetch = (await import('node-fetch')).default;

async function testCreation() {
  console.log('🧪 Testing Product Creation\n');
  
  const response = await fetch('http://localhost:5173/api/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      message: "Create a simple test product with title 'Simple Test Product', vendor 'Test Vendor', and product type 'Test Type'"
    })
  });
  
  const text = await response.text();
  const lines = text.split('\n');
  
  // Find the done event and extract the response
  for (let i = 0; i < lines.length; i++) {
    if (lines[i] === 'event: done' && lines[i+1]?.startsWith('data: ')) {
      const data = JSON.parse(lines[i+1].substring(6));
      console.log('Response:', data.finalResponse);
      break;
    }
  }
}

testCreation();