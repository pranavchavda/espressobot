#!/usr/bin/env node
/**
 * Test script for price monitor agent
 */

import { executePriceMonitorTask } from './server/agents/price-monitor-agent.js';

async function testPriceMonitorAgent() {
  console.log('🧪 Testing Price Monitor Agent...\n');
  
  const task = "Get the most severe MAP violations with detailed product info, listing violating SKU, brand/vendor, product type, current price, MAP price, and severity/ranking. Sort by most severe first.";
  
  console.log('📋 Task:', task);
  console.log('⏳ Executing...\n');
  
  try {
    const result = await executePriceMonitorTask(task, 'test-conversation-123', {
      userId: 'test-user'
    });
    
    console.log('✅ Result:', JSON.stringify(result, null, 2));
    
    if (result.success) {
      console.log('\n🎉 Price Monitor Agent test PASSED!');
    } else {
      console.log('\n❌ Price Monitor Agent test FAILED!');
      console.log('Error:', result.error);
    }
    
  } catch (error) {
    console.log('\n💥 Price Monitor Agent test CRASHED!');
    console.log('Error:', error.message);
    console.log('Stack:', error.stack);
  }
}

// Run the test
testPriceMonitorAgent().then(() => {
  console.log('\n🏁 Test completed');
  process.exit(0);
}).catch(error => {
  console.error('💥 Test script error:', error);
  process.exit(1);
});