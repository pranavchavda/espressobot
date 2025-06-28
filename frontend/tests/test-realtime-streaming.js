#!/usr/bin/env node

console.log('🔍 Testing Real-time Streaming\n');

const fetch = (await import('node-fetch')).default;

async function testRealtimeStreaming(message) {
  console.log(`Query: "${message}"\n`);
  console.log('Events as they arrive:');
  console.log('----------------------------');
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    let assistantContent = '';
    let eventTimeline = [];
    
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('event: ')) {
        const event = lines[i].substring(7);
        const timestamp = new Date().toISOString();
        
        if (lines[i+1]?.startsWith('data: ')) {
          try {
            const data = JSON.parse(lines[i+1].substring(6));
            
            if (event === 'assistant_delta') {
              assistantContent += data.delta;
              eventTimeline.push({
                time: timestamp,
                event: 'assistant_delta',
                contentLength: assistantContent.length,
                delta: data.delta
              });
            } else {
              eventTimeline.push({
                time: timestamp,
                event: event,
                data: JSON.stringify(data).substring(0, 50) + '...'
              });
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
    
    console.log('\nEvent Timeline:');
    eventTimeline.forEach((e, idx) => {
      if (e.event === 'assistant_delta') {
        console.log(`${idx + 1}. ${e.event} - Added "${e.delta}" (total: ${e.contentLength} chars)`);
      } else {
        console.log(`${idx + 1}. ${e.event} - ${e.data}`);
      }
    });
    
    console.log('\n----------------------------');
    console.log('Final assembled content:');
    console.log(assistantContent || '[No content received]');
    
  } catch (error) {
    console.error('Request failed:', error.message);
  }
}

await testRealtimeStreaming("What's 2+2? Think step by step.");

console.log('\n✅ Test completed!');