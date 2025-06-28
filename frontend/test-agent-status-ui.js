#!/usr/bin/env node

// Test the multi-agent status updates via the API
import fetch from 'node-fetch';

const API_URL = 'http://localhost:5174/api/agent/run';

async function testAgentStatus() {
  console.log('Testing multi-agent status updates...\n');
  
  const requestBody = {
    message: "Search for espresso machines and show me the top 3",
    conv_id: null,
    forceTaskGen: false,
    image: null
  };
  
  console.log('Sending request:', requestBody);
  console.log('\nExpected status sequence:');
  console.log('1. 🤔 Analyzing your request...');
  console.log('2. 🔍 Analyzing your request in detail...');
  console.log('3. 🧐 Determining the best approach...');
  console.log('4. 🧠 Checking conversation history...');
  console.log('5. 📝 Creating execution plan...');
  console.log('6. 🔎 Searching products...');
  console.log('\nListening for status events...\n');
  
  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('event: ')) {
          const eventName = line.substring(7);
          console.log(`\n📩 Event: ${eventName}`);
        } else if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6));
            
            // Highlight status events
            if (data.status || data.message) {
              console.log('📌 Status Update:');
              if (data.agent) console.log(`   Agent: ${data.agent}`);
              if (data.status) console.log(`   Status: ${data.status}`);
              if (data.message) console.log(`   Message: ${data.message}`);
              if (data.tool) console.log(`   Tool: ${data.tool}`);
            } else {
              console.log('   Data:', JSON.stringify(data, null, 2).substring(0, 200) + '...');
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
    
    console.log('\n✅ Test completed');
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
}

testAgentStatus();