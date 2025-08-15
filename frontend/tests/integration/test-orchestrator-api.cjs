#!/usr/bin/env node

const http = require('http');

const payload = JSON.stringify({
  message: "Search for Mexican Altura product",
  conversationId: "test-mcp-" + Date.now(),
  userId: "user_2"
});

const options = {
  hostname: 'localhost',
  port: 5173,
  path: '/api/agent/run',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Content-Length': payload.length,
    'X-Terminal-Request': 'true' // Bypass auth for localhost terminal requests
  }
};

console.log('Sending request to orchestrator...');
console.log('Payload:', payload);

const req = http.request(options, (res) => {
  console.log(`Status: ${res.statusCode}`);
  console.log(`Headers:`, res.headers);
  
  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
    // Print SSE events as they come
    const lines = chunk.toString().split('\n');
    lines.forEach(line => {
      if (line.startsWith('event:')) {
        console.log('\n[SSE Event]', line);
      } else if (line.startsWith('data:')) {
        try {
          const eventData = JSON.parse(line.substring(5));
          console.log('[SSE Data]', JSON.stringify(eventData, null, 2));
        } catch (e) {
          console.log('[SSE Data Raw]', line.substring(5));
        }
      }
    });
  });
  
  res.on('end', () => {
    console.log('\nResponse complete');
    if (data && !data.includes('event:')) {
      console.log('Raw response:', data);
    }
  });
});

req.on('error', (e) => {
  console.error(`Problem with request: ${e.message}`);
});

// Write data to request body
req.write(payload);
req.end();