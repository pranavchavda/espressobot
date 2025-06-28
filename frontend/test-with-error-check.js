import fetch from 'node-fetch';

async function testWithErrorCheck() {
  console.log('Testing Multi-Agent with error detection...\n');
  
  const testPayload = {
    conv_id: 'test-error-' + Date.now(),
    message: 'Hello',
    forceTaskGen: false
  };

  console.log('Sending simple message:', testPayload.message);
  console.log('---\n');

  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(testPayload)
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`HTTP ${response.status}: ${text}`);
    }

    // Handle SSE stream
    console.log('📡 Receiving events:\n');
    
    const reader = response.body;
    let buffer = '';
    const allEvents = [];
    let timeout = null;

    // Set a timeout to end after 5 seconds of no activity
    const resetTimeout = () => {
      if (timeout) clearTimeout(timeout);
      timeout = setTimeout(() => {
        console.log('\n⏱️ No events for 5 seconds, ending stream...');
        reader.cancel();
      }, 5000);
    };

    resetTimeout();

    try {
      for await (const chunk of reader) {
        resetTimeout();
        buffer += chunk.toString();
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventName = line.slice(7);
            console.log(`📨 Event: ${eventName}`);
            allEvents.push({ type: 'event', name: eventName });
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6);
            
            try {
              const parsed = JSON.parse(data);
              console.log(`   Data:`, JSON.stringify(parsed));
              allEvents.push({ type: 'data', content: parsed });
              
              // Check for errors
              if (parsed.error || parsed.message?.includes('Error') || parsed.message?.includes('error')) {
                console.log('\n❌ ERROR DETECTED IN STREAM!');
              }
            } catch (e) {
              if (data !== '[DONE]') {
                console.log(`   Raw: ${data}`);
                allEvents.push({ type: 'raw', content: data });
              }
            }
          }
        }
      }
    } catch (streamError) {
      if (streamError.name !== 'AbortError') {
        console.error('\n❌ Stream error:', streamError.message);
      }
    }

    clearTimeout(timeout);

    console.log(`\n\n📊 Final Summary:`);
    console.log(`Total events received: ${allEvents.length}`);
    
    const eventTypes = {};
    allEvents.forEach(e => {
      if (e.type === 'event') {
        eventTypes[e.name] = (eventTypes[e.name] || 0) + 1;
      }
    });
    
    console.log('\nEvent types:');
    Object.entries(eventTypes).forEach(([name, count]) => {
      console.log(`  ${name}: ${count}`);
    });

    // Check if we got stuck after start
    if (allEvents.length <= 2) {
      console.log('\n⚠️  WARNING: Very few events received!');
      console.log('Possible issues:');
      console.log('1. Agent initialization failed');
      console.log('2. OpenAI API key issue');
      console.log('3. Network/firewall blocking');
      console.log('4. Server-side error (check server logs)');
    }

  } catch (error) {
    console.error('\n❌ Request Error:', error.message);
    console.error('\nMake sure:');
    console.error('1. Dev server is running (npm run dev)');
    console.error('2. USE_MULTI_AGENT=true in .env');
    console.error('3. OPENAI_API_KEY is set correctly');
  }
}

// Run the test
testWithErrorCheck().catch(console.error);