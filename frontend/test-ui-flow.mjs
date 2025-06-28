console.log('🔍 Testing Full UI Flow\n');

const fetch = (await import('node-fetch')).default;

async function testUIFlow(message) {
  console.log(`Query: "${message}"\n`);
  console.log('Event Timeline:');
  console.log('----------------------------');
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    let timeline = [];
    let streamingContent = '';
    let finalResponse = '';
    
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].startsWith('event: ')) {
        const event = lines[i].substring(7);
        const timestamp = Date.now();
        
        if (lines[i+1]?.startsWith('data: ')) {
          try {
            const data = JSON.parse(lines[i+1].substring(6));
            
            if (event === 'assistant_delta') {
              streamingContent += data.delta || '';
              timeline.push({
                event: 'assistant_delta',
                time: timestamp,
                contentSoFar: streamingContent.length + ' chars'
              });
            } else if (event === 'done') {
              finalResponse = data.finalResponse || '';
              timeline.push({
                event: 'done',
                time: timestamp,
                hasFinalResponse: !!data.finalResponse
              });
            } else {
              timeline.push({
                event: event,
                time: timestamp
              });
            }
          } catch (e) {}
        }
      }
    }
    
    // Display timeline
    let baseTime = timeline[0]?.time || 0;
    timeline.forEach((entry, idx) => {
      const relTime = entry.time - baseTime;
      console.log(`${idx + 1}. [+${relTime}ms] ${entry.event}`, 
        entry.contentSoFar ? `(${entry.contentSoFar})` : 
        entry.hasFinalResponse !== undefined ? `(finalResponse: ${entry.hasFinalResponse})` : '');
    });
    
    console.log('\n----------------------------');
    console.log('Streaming Content Length:', streamingContent.length);
    console.log('Streaming Content:', streamingContent ? 'YES' : 'NO');
    console.log('Final Response in done:', finalResponse ? 'YES' : 'NO');
    console.log('Content Match:', streamingContent === finalResponse ? 'YES' : 'NO');
    
    console.log('\n📝 Analysis:');
    const hasDelta = timeline.some(e => e.event === 'assistant_delta');
    const hasDone = timeline.some(e => e.event === 'done');
    
    if (!hasDelta) {
      console.log('❌ No assistant_delta events - content won\'t stream');
    } else if (!streamingContent) {
      console.log('❌ assistant_delta events exist but no content');
    } else if (hasDelta && hasDone && streamingContent) {
      console.log('✅ Proper streaming flow detected');
    }
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

// Test
await testUIFlow("Hello, how are you?");

console.log('\n✅ Test completed!');