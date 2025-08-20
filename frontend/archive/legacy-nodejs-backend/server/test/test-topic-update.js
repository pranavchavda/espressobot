import { updateConversationTopic } from '../tools/update-conversation-topic.js';

console.log('=== Testing Topic Update System ===\n');

// Mock global SSE emitter
let emittedEvents = [];
global.currentSseEmitter = (event, data) => {
  emittedEvents.push({ event, data });
  console.log(`SSE Event emitted: ${event}`, data);
};

// Test topic update
async function testTopicUpdate() {
  console.log('1. Testing topic update function:');
  
  try {
    // This will fail with database error but we can see if SSE event is emitted
    const result = await updateConversationTopic({
      conversation_id: '123',
      topic_title: 'Test Topic: Product Price Updates',
      topic_details: 'Discussion about updating prices for coffee products'
    });
    
    console.log('Result:', result);
  } catch (error) {
    console.log('Expected database error:', error.message);
  }
  
  console.log('\n2. Checking SSE events:');
  console.log('Events emitted:', emittedEvents.length);
  emittedEvents.forEach(({ event, data }) => {
    console.log(`- Event: ${event}`);
    console.log(`  Data:`, data);
  });
  
  console.log('\n3. Expected frontend behavior:');
  console.log('- StreamingChatPage receives topic_updated event');
  console.log('- Calls onTopicUpdate callback with conversation_id, topic_title, topic_details');
  console.log('- App.jsx updates conversations state');
  console.log('- Sidebar displays topic_title instead of truncated first message');
}

testTopicUpdate().catch(console.error);