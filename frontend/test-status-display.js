import fetch from 'node-fetch';

async function testStatusDisplay() {
  console.log('Testing Multi-Agent Status Display...\n');
  
  const testPayload = {
    conv_id: 'test-status-' + Date.now(),
    message: 'Search for Breville Barista Express',
    forceTaskGen: false
  };

  console.log('Sending request:', testPayload.message);
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
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Handle SSE stream
    console.log('📡 Receiving events:\n');
    
    const reader = response.body;
    let buffer = '';
    let eventCount = 0;
    let statusCount = 0;

    for await (const chunk of reader) {
      buffer += chunk.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventName = line.slice(7);
          eventCount++;
          
          // Color code different event types
          if (eventName === 'agent_status' || eventName === 'agent_processing') {
            console.log(`\n🔵 [${eventName}]`);
            statusCount++;
          } else if (eventName === 'handoff') {
            console.log(`\n🔀 [${eventName}]`);
          } else if (eventName === 'tool_call') {
            console.log(`\n🔧 [${eventName}]`);
          } else if (eventName === 'response') {
            process.stdout.write(`\n📝 [${eventName}] `);
          } else if (eventName === 'done') {
            console.log(`\n✅ [${eventName}]`);
            return;
          } else {
            console.log(`\n⚪ [${eventName}]`);
          }
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6);
          
          try {
            const parsed = JSON.parse(data);
            
            // Format output based on content
            if (parsed.message) {
              console.log(`   "${parsed.message}"`);
            } else if (parsed.agent && parsed.tool) {
              console.log(`   ${parsed.agent} → ${parsed.tool}`);
            } else if (parsed.from && parsed.to) {
              console.log(`   ${parsed.from} → ${parsed.to}`);
            } else if (typeof parsed === 'string') {
              // Response chunks
              process.stdout.write(parsed);
            } else {
              console.log(`   ${JSON.stringify(parsed)}`);
            }
          } catch (e) {
            if (data !== '[DONE]') {
              console.log(`   ${data}`);
            }
          }
        }
      }
    }

    console.log(`\n\n📊 Summary:`);
    console.log(`Total events: ${eventCount}`);
    console.log(`Status events: ${statusCount}`);
    console.log(`\nIf status events = 0, the UI would show "Generating..."`);
    console.log(`If status events > 0, the UI should show the actual status messages`);

  } catch (error) {
    console.error('\n❌ Error:', error.message);
    console.error('\nMake sure the dev server is running (npm run dev)');
  }
}

// Run the test
console.log('🧪 Multi-Agent Status Display Test\n');
console.log('This test will show what status events are being sent by the backend');
console.log('===================================================================\n');

testStatusDisplay().catch(console.error);