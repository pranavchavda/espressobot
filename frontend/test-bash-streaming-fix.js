#!/usr/bin/env node

console.log('🔍 Testing Bash Orchestrator Streaming Fix\n');

const fetch = (await import('node-fetch')).default;

async function testBashStreaming() {
  const query = "Run this command: echo 'Hello from bash orchestrator'";
  console.log(`Query: "${query}"\n`);
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: query })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    // Track different event types
    const events = {
      start: 0,
      agent_processing: 0,
      assistant_delta: 0,
      tool_call: 0,
      done: 0,
      other: 0
    };
    
    let content = '';
    
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('event: ')) {
        const eventType = lines[i].substring(7);
        
        if (events[eventType] !== undefined) {
          events[eventType]++;
        } else {
          events.other++;
        }
        
        if (eventType === 'assistant_delta' && lines[i+1]?.startsWith('data: ')) {
          try {
            const data = JSON.parse(lines[i+1].substring(6));
            content += data.delta || '';
          } catch (e) {}
        }
      }
    }
    
    console.log('Event Summary:');
    console.log('-------------');
    Object.entries(events).forEach(([event, count]) => {
      if (count > 0) {
        console.log(`${event}: ${count}`);
      }
    });
    
    console.log('\nStreamed Content:');
    console.log('-----------------');
    console.log(content || '[No content streamed]');
    
    // Key indicators
    console.log('\n✓ Real-time streaming:', events.assistant_delta > 0 ? 'YES' : 'NO');
    console.log('✓ Done event sent:', events.done > 0 ? 'YES' : 'NO');
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

await testBashStreaming();
console.log('\n✅ Test completed!');