import fetch from 'node-fetch';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Create a simple red square image for testing
const redSquareBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';

async function testMultiAgentVision() {
  console.log('Testing Multi-Agent Vision with Base64 Image...\n');
  
  const testPayload = {
    conv_id: 'test-vision-' + Date.now(),
    message: 'What color is the square in this image? Please describe what you see.',
    forceTaskGen: false,
    image: {
      type: 'data_url',
      data: `data:image/png;base64,${redSquareBase64}`
    }
  };

  console.log('Sending request to multi-agent orchestrator...');
  console.log('Conversation ID:', testPayload.conv_id);
  console.log('Message:', testPayload.message);
  console.log('Image type:', testPayload.image.type);
  console.log('Image size:', testPayload.image.data.length, 'characters\n');

  try {
    const response = await fetch('http://localhost:3001/api/multi-agent/run', {
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
    console.log('Receiving response stream...\n');
    
    const reader = response.body;
    let buffer = '';
    let messageCount = 0;
    let sawImage = false;
    let finalResponse = '';

    for await (const chunk of reader) {
      buffer += chunk.toString();
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') {
            console.log('\n[STREAM COMPLETE]');
            break;
          }

          try {
            const event = JSON.parse(data);
            messageCount++;

            // Log different event types
            if (event.type === 'agent_processing') {
              console.log(`[${event.type}] ${event.data.agent}: ${event.data.message}`);
            } else if (event.type === 'handoff') {
              console.log(`[${event.type}] ${event.data.from} → ${event.data.to}`);
            } else if (event.type === 'status') {
              console.log(`[${event.type}] ${event.data.message}`);
              if (event.data.message.includes('vision')) {
                sawImage = true;
              }
            } else if (event.type === 'response') {
              finalResponse += event.data;
              process.stdout.write(event.data);
            } else if (event.type === 'tool_call') {
              console.log(`[${event.type}] ${event.data.agent} calling ${event.data.tool}`);
            } else if (event.type === 'error') {
              console.error(`[ERROR] ${event.data.message}`);
            }
          } catch (e) {
            // Ignore parse errors for incomplete chunks
          }
        }
      }
    }

    console.log('\n\nTest Results:');
    console.log('=============');
    console.log('Total events received:', messageCount);
    console.log('Vision processing detected:', sawImage ? '✅ Yes' : '❌ No');
    
    // Check if the response mentions the correct color
    const lowerResponse = finalResponse.toLowerCase();
    const sawRed = lowerResponse.includes('red');
    const sawWrongColor = ['blue', 'green', 'yellow', 'purple', 'orange'].some(c => lowerResponse.includes(c));
    
    console.log('Correct color identified:', sawRed ? '✅ Yes (Red)' : '❌ No');
    if (sawWrongColor) {
      console.log('⚠️  Wrong color mentioned in response');
    }
    
    console.log('\nTest', sawRed && !sawWrongColor ? 'PASSED ✅' : 'FAILED ❌');

  } catch (error) {
    console.error('Test failed with error:', error.message);
    console.error(error.stack);
  }
}

// Run the test
console.log('Starting Multi-Agent Vision Test');
console.log('================================\n');

testMultiAgentVision().catch(console.error);