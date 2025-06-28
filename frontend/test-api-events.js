#!/usr/bin/env node

console.log('🧪 API Event Stream Test\n');

const fetch = (await import('node-fetch')).default;

async function captureAllEvents(message) {
  console.log(`Query: "${message}"\n`);
  console.log('Events received:');
  
  const response = await fetch('http://localhost:5173/api/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const text = await response.text();
  const lines = text.split('\n');
  
  let eventCount = {
    handoff: 0,
    tool_call: 0,
    agent_processing: 0,
    agent_message: 0
  };
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (line.startsWith('event: ')) {
      const eventType = line.substring(7);
      const dataLine = lines[i + 1];
      
      if (dataLine && dataLine.startsWith('data: ')) {
        try {
          const data = JSON.parse(dataLine.substring(6));
          
          if (eventType === 'handoff') {
            eventCount.handoff++;
            console.log(`  🔄 HANDOFF: ${data.from} → ${data.to}`);
          } else if (eventType === 'tool_call') {
            eventCount.tool_call++;
            console.log(`  🔧 TOOL: ${data.agent} uses ${data.tool}`);
          } else if (eventType === 'agent_processing') {
            eventCount.agent_processing++;
            console.log(`  🤖 AGENT: ${data.agent} - ${data.message || 'Processing'}`);
          } else if (eventType === 'agent_message') {
            eventCount.agent_message++;
            console.log(`  💬 MESSAGE from ${data.agent || 'Agent'}`);
          }
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
  }
  
  console.log('\nEvent Summary:');
  Object.entries(eventCount).forEach(([event, count]) => {
    console.log(`  ${event}: ${count}`);
  });
}

// Test different queries
async function runTests() {
  await captureAllEvents("Search for coffee grinders");
  console.log('\n' + '='.repeat(50) + '\n');
  
  await captureAllEvents("Create a product called Test Demo Product");
  console.log('\n' + '='.repeat(50) + '\n');
  
  await captureAllEvents("I need help with inventory management");
}

runTests();