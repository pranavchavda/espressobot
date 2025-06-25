#!/usr/bin/env node

// Debug script to see what events the multi-agent orchestrator is sending

import fetch from 'node-fetch';

async function debugMultiAgentStream() {
  console.log('🔍 Debugging Multi-Agent Event Stream...\n');
  
  const testMessage = "Hello, can you help me search for Eureka products?";
  
  console.log('📝 Sending test message:', testMessage);
  
  try {
    const response = await fetch('http://localhost:3001/api/multi-agent/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: testMessage,
        conv_id: 999 // Test conversation ID
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    console.log('\n📡 Received SSE Events:\n');
    
    let eventCount = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          eventCount++;
          const eventName = line.substring(7);
          console.log(`\n[Event #${eventCount}] ${eventName}`);
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6));
            console.log('  Data:', JSON.stringify(data, null, 2));
          } catch (e) {
            console.log('  Raw data:', line.substring(6));
          }
        }
      }
    }
    
    console.log(`\n✅ Stream completed. Total events: ${eventCount}`);
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

// Run the debug script
debugMultiAgentStream();