#!/usr/bin/env node

import { runDynamicOrchestrator } from './server/espressobot1.js';

// Create a mock SSE emitter that logs events
const mockSseEmitter = (event, data) => {
  console.log(`\n📡 SSE Event: ${event}`);
  console.log('Data:', JSON.stringify(data, null, 2));
};

async function testBashCallbacks() {
  console.log('🧪 Testing Bash Orchestrator Callbacks\n');
  
  try {
    // Test message that should spawn a bash agent
    const testMessage = 'Use bash to check what Python tools are available in /home/pranav/idc/tools/';
    
    console.log('Sending test message:', testMessage);
    console.log('---');
    
    const result = await runDynamicOrchestrator(testMessage, {
      conversationId: 'test-123',
      sseEmitter: mockSseEmitter
    });
    
    console.log('\n✅ Test completed!');
    console.log('Final result:', result?.state?._currentStep?.output || result);
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    console.error(error.stack);
  }
}

// Run the test
testBashCallbacks();