import fetch from 'node-fetch';

async function testMultiAgentStatus() {
  console.log('Testing Multi-Agent Status Updates...\n');
  
  const testPayload = {
    conv_id: 'test-status-' + Date.now(),
    message: 'Find all Breville espresso machines',
    forceTaskGen: false
  };

  console.log('Sending request to multi-agent endpoint...');
  console.log('Message:', testPayload.message);
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
    console.log('Receiving SSE events:\n');
    
    const reader = response.body;
    let buffer = '';
    const events = [];
    let currentEventName = null;

    for await (const chunk of reader) {
      buffer += chunk.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event: ')) {
          currentEventName = line.slice(7);
          console.log(`📨 Event: ${currentEventName}`);
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            console.log('\n✅ Stream complete');
            return; // Exit the entire stream processing
          }

          try {
            const parsed = JSON.parse(data);
            
            // Log status updates specially
            if (parsed.status || parsed.message) {
              console.log(`   📍 Status: ${parsed.message || parsed.status}`);
            }
            
            // Track all events
            events.push({ event: currentEventName || 'data', ...parsed });
          } catch (e) {
            console.log(`   Raw: ${data}`);
          }
        }
      }
    }

    console.log('\n\nSummary of Events Received:');
    console.log('=========================');
    
    const statusEvents = events.filter(e => 
      e.type === 'agent_status' || 
      e.type === 'agent_processing' || 
      e.type === 'tool_call' ||
      e.type === 'handoff'
    );
    
    console.log(`Total events: ${events.length}`);
    console.log(`Status-related events: ${statusEvents.length}`);
    
    if (statusEvents.length > 0) {
      console.log('\nStatus Events:');
      statusEvents.forEach((e, i) => {
        console.log(`${i+1}. ${e.type}: ${e.message || e.status || JSON.stringify(e)}`);
      });
    }

  } catch (error) {
    console.error('Test failed:', error.message);
    console.error('\nMake sure the server is running on port 3001');
  }
}

// Run the test
testMultiAgentStatus().catch(console.error);