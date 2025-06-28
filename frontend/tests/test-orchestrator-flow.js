#\!/usr/bin/env node

console.log('🔍 Testing Orchestrator Flow\n');

const fetch = (await import('node-fetch')).default;

async function testOrchestratorFlow(message) {
  console.log(`Query: "${message}"\n`);
  console.log('Event Flow:');
  console.log('----------');
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    let eventSequence = [];
    let finalResponse = '';
    
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('event: ')) {
        const event = lines[i].substring(7);
        
        if (lines[i+1]?.startsWith('data: ')) {
          try {
            const data = JSON.parse(lines[i+1].substring(6));
            
            if (event === 'agent_processing') {
              eventSequence.push(`Agent: ${data.agent} - ${data.message}`);
            } else if (event === 'tool_call') {
              eventSequence.push(`Tool: ${data.name} (${data.status})`);
            } else if (event === 'assistant_delta') {
              eventSequence.push(`Delta: "${data.delta}"`);
            } else if (event === 'done') {
              finalResponse = data.finalResponse;
              eventSequence.push(`Done: Response saved`);
            } else {
              eventSequence.push(`${event}: ${JSON.stringify(data).substring(0, 50)}...`);
            }
          } catch (e) {}
        }
      }
    }
    
    eventSequence.forEach((event, idx) => {
      console.log(`${idx + 1}. ${event}`);
    });
    
    console.log('\n----------');
    console.log('Final Response from done event:');
    console.log(finalResponse || '[No response in done event]');
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Test with a simple question that should trigger the orchestrator
await testOrchestratorFlow("What is 2+2?");

console.log('\n✅ Test completed\!');
