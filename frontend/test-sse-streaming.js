#!/usr/bin/env node

console.log('🔍 Testing SSE Streaming\n');

const fetch = (await import('node-fetch')).default;

async function testSSE(message) {
  console.log(`Query: "${message}"\n`);
  console.log('Events received:');
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    let eventCount = 0;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('event: ')) {
        eventCount++;
        const event = lines[i].substring(7);
        console.log(`${eventCount}. ${event}`);
        
        // Show data for key events
        if (['done', 'error', 'agent_processing'].includes(event) && lines[i+1]?.startsWith('data: ')) {
          try {
            const data = JSON.parse(lines[i+1].substring(6));
            if (event === 'done') {
              console.log('   Final response:', data.finalResponse?.substring(0, 100) + '...');
            } else if (event === 'error') {
              console.log('   Error:', data.message);
            } else if (event === 'agent_processing') {
              console.log('   Agent:', data.agent);
            }
          } catch (e) {
            console.log('   [parse error]');
          }
        }
      }
    }
    
    console.log(`\nTotal events: ${eventCount}`);
    
  } catch (error) {
    console.error('Request failed:', error.message);
  }
}

await testSSE("List Python tools with 'search' in the name");

console.log('\n✅ Test completed!');