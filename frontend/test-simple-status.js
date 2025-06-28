// Simple test to verify status updates are working
import { run } from '@openai/agents';
import { espressoBotOrchestrator } from './server/agents/espressobot-orchestrator.js';

console.log('Testing status updates directly...\n');

// Create a simple test context
const context = {
  conversationId: 'test-123',
  sseEmitter: {
    emit: (event, data) => {
      console.log(`📩 Event: ${event}`);
      console.log(`   Data:`, data);
    }
  }
};

// Mock sendEvent function
global.sendEvent = (event, data) => {
  console.log(`\n🚀 Status Event: ${event}`);
  if (data.message) {
    console.log(`   📌 Message: ${data.message}`);
  }
  if (data.agent) {
    console.log(`   👤 Agent: ${data.agent}`);
  }
  if (data.status) {
    console.log(`   📊 Status: ${data.status}`);
  }
};

try {
  console.log('Starting agent run...\n');
  
  const result = await run(espressoBotOrchestrator, 'Hello, test the status system', {
    maxTurns: 1,
    context
  });
  
  console.log('\n✅ Test completed');
  console.log('Result:', result?.state?._currentStep?.output || 'No output');
} catch (error) {
  console.error('\n❌ Error:', error.message);
}

process.exit(0);