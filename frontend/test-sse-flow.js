#!/usr/bin/env node

// Test if SSE events are being sent properly

import express from 'express';

const app = express();

app.get('/test-sse', (req, res) => {
  console.log('SSE test endpoint hit');
  
  // Set up SSE headers
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Access-Control-Allow-Origin': '*',
  });
  
  // Helper to send SSE events
  const sendEvent = (eventName, data) => {
    console.log(`Sending SSE event: ${eventName}`, data);
    res.write(`event: ${eventName}\ndata: ${JSON.stringify(data)}\n\n`);
  };
  
  // Send test events
  sendEvent('start', { message: 'Test started' });
  
  setTimeout(() => {
    sendEvent('agent_processing', {
      agent: 'Test_Agent',
      message: 'Test Agent is processing...',
      status: 'processing'
    });
  }, 1000);
  
  setTimeout(() => {
    sendEvent('task_plan_created', {
      agent: 'Task_Planner',
      markdown: '# Test Plan\n\n- [ ] Task 1\n- [ ] Task 2',
      taskCount: 2
    });
  }, 2000);
  
  setTimeout(() => {
    sendEvent('done', { message: 'Test complete' });
    res.end();
  }, 3000);
});

const PORT = 3002;
app.listen(PORT, () => {
  console.log(`SSE test server running on http://localhost:${PORT}/test-sse`);
  console.log('Test with: curl -N http://localhost:3002/test-sse');
});