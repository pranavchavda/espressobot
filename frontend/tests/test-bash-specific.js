#!/usr/bin/env node

console.log('🔍 Testing Specific Bash Commands\n');

const fetch = (await import('node-fetch')).default;

async function testBashCommand(query) {
  console.log(`\nQuery: "${query}"`);
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: query })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    // Find the done event
    for (let i = lines.length - 1; i >= 0; i--) {
      if (lines[i] === 'event: done' && lines[i+1]?.startsWith('data: ')) {
        const data = JSON.parse(lines[i+1].substring(6));
        console.log('Response:', data.finalResponse);
        break;
      }
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Test different commands
await testBashCommand("Run this exact bash command: ls /home/pranav/idc/tools/ | grep product");
await testBashCommand("What files are in /home/pranav/idc/tools/?");
await testBashCommand("Execute: cd /home/pranav/idc/tools && ls *.py | grep product");

console.log('\n✅ Tests completed!');