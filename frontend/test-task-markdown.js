#!/usr/bin/env node

// Test script to verify task markdown display is working

import fetch from 'node-fetch';

async function testTaskMarkdownFlow() {
  console.log('🧪 Testing Task Markdown Display Flow...\n');
  
  const testMessage = "Please create a plan to search for Eureka Mignon Zero products and display their prices. Use the task planner to organize this.";
  
  console.log('📝 Sending test message:', testMessage);
  console.log('🔄 This should trigger:');
  console.log('   1. Task Planner Agent to create a markdown plan');
  console.log('   2. Real-time display of the markdown in the UI');
  console.log('   3. Task markdown saved with the assistant message\n');
  
  try {
    const response = await fetch('http://localhost:3001/api/multi-agent/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: testMessage,
        conv_id: `test_${Date.now()}`
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    console.log('📡 Listening for SSE events:\n');
    
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('event: task_plan_creating')) {
          console.log('✅ Task Plan Creating event received');
        } else if (line.startsWith('event: task_plan_created')) {
          console.log('✅ Task Plan Created event received');
          const dataLine = lines[lines.indexOf(line) + 1];
          if (dataLine && dataLine.startsWith('data: ')) {
            const data = JSON.parse(dataLine.substring(6));
            console.log(`   - Filename: ${data.filename}`);
            console.log(`   - Task Count: ${data.taskCount}`);
            console.log(`   - Markdown Preview: ${data.markdown.substring(0, 100)}...`);
          }
        }
      }
    }
    
    console.log('\n✅ Test completed successfully!');
    console.log('📋 Next steps:');
    console.log('   1. Check the UI to see the task markdown display');
    console.log('   2. Verify the markdown appears during agent execution');
    console.log('   3. Confirm the markdown is saved with the message after completion');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

// Run the test
testTaskMarkdownFlow();