#!/usr/bin/env node

console.log('🧪 Testing Bash Orchestrator via API\n');

const fetch = (await import('node-fetch')).default;

async function testBashAPI(message) {
  console.log(`Query: "${message}"\n`);
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    // Parse events
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('event: ')) {
        const event = lines[i].substring(7);
        const dataLine = lines[i+1];
        
        if (dataLine?.startsWith('data: ')) {
          try {
            const data = JSON.parse(dataLine.substring(6));
            
            if (event === 'error') {
              console.log('❌ Error:', data.message);
            } else if (event === 'done') {
              console.log('Response:', data.finalResponse);
            } else if (event === 'agent_processing') {
              console.log('Agent:', data.agent, '-', data.message);
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
    
  } catch (error) {
    console.error('Request failed:', error.message);
  }
}

// Test
console.log('Make sure USE_BASH_ORCHESTRATOR=true is set!\n');
await testBashAPI("List the Python tools available in /home/pranav/idc/tools/ that contain 'product' in the filename");

console.log('\n✅ Test completed!');