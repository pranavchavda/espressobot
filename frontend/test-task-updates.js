#!/usr/bin/env node

/**
 * Test script to verify task update SSE events are working
 */

import fetch from 'node-fetch';

async function testTaskUpdates() {
  const token = process.env.AUTH_TOKEN || '';
  
  console.log('Testing task update SSE events...\n');
  
  // Create a test request that needs planning
  const requestData = {
    message: "First, search for all coffee products. Then update their prices by 10%. Finally, generate a report of the changes.",
    forceTaskGen: true
  };
  
  console.log('Sending request:', requestData.message);
  console.log('---');
  
  try {
    const response = await fetch('http://localhost:3000/api/agent/run', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const reader = response.body;
    const decoder = new TextDecoder();
    let buffer = '';
    let conversationId = null;
    let taskCount = 0;
    
    for await (const chunk of reader) {
      buffer += decoder.decode(chunk, { stream: true });
      
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      
      for (const eventBlock of lines) {
        if (!eventBlock.trim()) continue;
        
        let eventName = null;
        let eventData = null;
        
        const eventLines = eventBlock.split('\n');
        for (const line of eventLines) {
          if (line.startsWith('event:')) {
            eventName = line.substring(6).trim();
          } else if (line.startsWith('data:')) {
            try {
              eventData = JSON.parse(line.substring(5).trim());
            } catch (e) {
              console.error('Failed to parse event data:', line);
            }
          }
        }
        
        // Log relevant events
        if (eventName === 'conversation_id') {
          conversationId = eventData.conv_id;
          console.log(`✓ Conversation ID: ${conversationId}`);
        } else if (eventName === 'task_plan_created') {
          taskCount = eventData.taskCount;
          console.log(`✓ Task plan created with ${taskCount} tasks`);
          console.log('  Markdown:', eventData.markdown?.split('\n').slice(0, 3).join('\n'));
        } else if (eventName === 'task_summary') {
          console.log(`✓ Task summary event received:`);
          eventData.tasks?.forEach((task, idx) => {
            console.log(`  ${idx + 1}. [${task.status}] ${task.content} (${task.id})`);
          });
        } else if (eventName === 'agent_processing') {
          console.log(`⚙️  ${eventData.agent}: ${eventData.message}`);
        } else if (eventName === 'done') {
          console.log('\n✓ Request completed');
          break;
        }
      }
    }
    
    console.log('\n---');
    console.log('Test completed successfully!');
    console.log('Check the frontend to verify task status updates are visible.');
    
  } catch (error) {
    console.error('Error:', error);
  }
}

// Run the test
testTaskUpdates().catch(console.error);