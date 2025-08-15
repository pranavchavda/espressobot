import { buildCompressedContext } from '../agents/conversation-summarizer-agent.js';

// Test data - simulate a long conversation
const generateTestMessages = (count) => {
  const messages = [];
  const topics = [
    'Looking for a new espresso machine',
    'Comparing Breville and Sanremo models',
    'Discussing pricing and discounts',
    'Asking about inventory and shipping',
    'Setting up bulk pricing',
    'Configuring product variants',
    'Managing inventory policies',
    'Creating product bundles'
  ];
  
  for (let i = 0; i < count; i++) {
    const topicIndex = Math.floor(i / 4) % topics.length;
    const isUser = i % 2 === 0;
    
    if (isUser) {
      messages.push({
        role: 'user',
        content: `${topics[topicIndex]} - message ${i + 1}. Can you help me with this?`
      });
    } else {
      messages.push({
        role: 'assistant',
        content: `I'll help you with ${topics[topicIndex]}. Here's what I found - message ${i + 1}. [Details about the topic...]`
      });
    }
  }
  
  return messages;
};

async function testCompression() {
  console.log('=== Testing Conversation Compression ===\n');
  
  // Test 1: Short conversation (no compression needed)
  console.log('Test 1: Short conversation (6 messages)');
  const shortMessages = generateTestMessages(6);
  const shortResult = await buildCompressedContext(shortMessages);
  console.log(`- Total messages: ${shortResult.totalMessages}`);
  console.log(`- Summarized: ${shortResult.summarizedCount || 0}`);
  console.log(`- Recent messages kept: ${shortResult.recentMessages.length}`);
  console.log(`- Has summary: ${!!shortResult.finalSummary}\n`);
  
  // Test 2: Medium conversation (needs 1 summary)
  console.log('Test 2: Medium conversation (16 messages)');
  const mediumMessages = generateTestMessages(16);
  const mediumResult = await buildCompressedContext(mediumMessages);
  console.log(`- Total messages: ${mediumResult.totalMessages}`);
  console.log(`- Summarized: ${mediumResult.summarizedCount}`);
  console.log(`- Recent messages kept: ${mediumResult.recentMessages.length}`);
  console.log(`- Number of summaries: ${mediumResult.summaries.length}`);
  if (mediumResult.finalSummary) {
    console.log('- Final summary type:', typeof mediumResult.finalSummary);
    console.log('- Final summary keys:', Object.keys(mediumResult.finalSummary));
    if (mediumResult.finalSummary.summary) {
      const summaryText = typeof mediumResult.finalSummary.summary === 'string' 
        ? mediumResult.finalSummary.summary 
        : JSON.stringify(mediumResult.finalSummary.summary);
      console.log(`- Summary preview: "${summaryText.substring(0, 100)}..."`);
    } else {
      console.log('- No summary text found in finalSummary');
    }
  }
  console.log();
  
  // Test 3: Long conversation (needs multiple summaries)
  console.log('Test 3: Long conversation (32 messages)');
  const longMessages = generateTestMessages(32);
  const longResult = await buildCompressedContext(longMessages);
  console.log(`- Total messages: ${longResult.totalMessages}`);
  console.log(`- Summarized: ${longResult.summarizedCount}`);
  console.log(`- Recent messages kept: ${longResult.recentMessages.length}`);
  console.log(`- Number of summaries: ${longResult.summaries.length}`);
  if (longResult.finalSummary) {
    console.log(`- Summary length: ${longResult.finalSummary.summary.length} chars`);
    console.log(`- Key points: ${longResult.finalSummary.keyPoints?.length || 0}`);
    console.log(`- Pending items: ${longResult.finalSummary.pendingItems?.length || 0}`);
  }
  console.log();
  
  // Test 4: Very long conversation to test recursive summarization
  console.log('Test 4: Very long conversation (64 messages)');
  const veryLongMessages = generateTestMessages(64);
  const veryLongResult = await buildCompressedContext(veryLongMessages);
  console.log(`- Total messages: ${veryLongResult.totalMessages}`);
  console.log(`- Summarized: ${veryLongResult.summarizedCount}`);
  console.log(`- Recent messages kept: ${veryLongResult.recentMessages.length}`);
  console.log(`- Number of summaries: ${veryLongResult.summaries.length}`);
  
  // Show how summaries are chunked
  veryLongResult.summaries.forEach((summary, idx) => {
    console.log(`  - Chunk ${idx + 1}: messages ${summary.startIndex + 1}-${summary.endIndex}`);
  });
  
  if (veryLongResult.finalSummary) {
    console.log(`- Combined summary length: ${veryLongResult.finalSummary.summary.length} chars`);
  }
  
  console.log('\n=== Compression Test Complete ===');
}

// Run the test
testCompression().catch(console.error);