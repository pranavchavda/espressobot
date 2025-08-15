import { updateConversationTopic } from '../tools/update-conversation-topic.js';

// Mock SSE emitter
let sseEvents = [];
global.currentSseEmitter = (event, data) => {
  console.log(`SSE Event: ${event}`, data);
  sseEvents.push({ event, data });
};

async function testTopicUpdateFlow() {
  console.log('=== Testing Topic Update Flow ===\n');
  
  // Test updating conversation 279
  const result = await updateConversationTopic({
    conversation_id: '279',
    topic_title: 'Testing Topic Update Flow',
    topic_details: 'This is a test to see if the SSE events are working correctly'
  });
  
  console.log('\nUpdate result:', result);
  console.log('\nSSE events emitted:', sseEvents);
  
  process.exit(0);
}

testTopicUpdateFlow().catch(console.error);