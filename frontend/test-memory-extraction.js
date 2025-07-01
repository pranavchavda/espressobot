#!/usr/bin/env node
/**
 * Test memory extraction with GPT-4.1-mini/nano
 */

import { memoryOperations } from './server/memory/memory-operations-local.js';

const testConversation1 = `User: Hi, my name is Pranav and I manage the iDrinkCoffee.com store. I particularly enjoy Ethiopian Yirgacheffe coffee.
Assistant: Hello Pranav! It's great to meet you. Ethiopian Yirgacheffe is an excellent choice - it's known for its bright, wine-like acidity and floral notes. As the manager of iDrinkCoffee.com, do you carry Yirgacheffe in your store?

User: Yes, we do! We offer 15% bulk discounts on combo products. By the way, who is the CEO?
Assistant: The CEO of iDrinkCoffee.com is Slawek Janicki. That's a generous 15% bulk discount on combo products - it's a great way to encourage larger purchases!`;

const testConversation2 = `User: Can you update the pricing for our Breville machines?
Assistant: I'll help you update the pricing for Breville machines. Let me search for all Breville products first.

User: Actually, let's increase all espresso machine prices by 10% and I prefer to review changes before applying them.
Assistant: Understood. I'll prepare a list of all espresso machines with the 10% price increase for your review before making any changes. This aligns with your preference to review pricing updates before applying them.`;

async function testExtraction() {
  console.log('=== Testing Memory Extraction ===\n');
  
  try {
    // Test extraction from conversation 1
    console.log('Extracting from Conversation 1...');
    const facts1 = await memoryOperations.extractMemorySummary(testConversation1, {
      conversationId: 'test-1',
      agent: 'test'
    });
    
    console.log(`\nExtracted ${facts1.length} facts:`);
    facts1.forEach((fact, i) => {
      console.log(`${i + 1}. ${fact.content}`);
    });
    
    // Test extraction from conversation 2
    console.log('\n\nExtracting from Conversation 2...');
    const facts2 = await memoryOperations.extractMemorySummary(testConversation2, {
      conversationId: 'test-2',
      agent: 'test'
    });
    
    console.log(`\nExtracted ${facts2.length} facts:`);
    facts2.forEach((fact, i) => {
      console.log(`${i + 1}. ${fact.content}`);
    });
    
    // Test with nano model
    console.log('\n\nTesting with GPT-4.1-nano...');
    const factsNano = await memoryOperations.extractMemorySummary(testConversation1, {
      conversationId: 'test-nano',
      agent: 'test',
      useNano: true
    });
    
    console.log(`\nExtracted ${factsNano.length} facts with nano:`);
    factsNano.forEach((fact, i) => {
      console.log(`${i + 1}. ${fact.content}`);
    });
    
    // Test storage with deduplication
    console.log('\n\nTesting storage with deduplication...');
    const userId = 'test_user';
    
    // Store first fact
    const result1 = await memoryOperations.add(facts1[0].content, userId, facts1[0].metadata);
    console.log('First storage:', result1.success ? 'Success' : 'Failed');
    
    // Try to store same fact again
    const result2 = await memoryOperations.add(facts1[0].content, userId, facts1[0].metadata);
    console.log('Duplicate storage:', result2.success ? 'Success' : `Failed - ${result2.reason}`);
    
    // Clean up test data
    await memoryOperations.deleteAll(userId);
    console.log('\nTest data cleaned up');
    
  } catch (error) {
    console.error('Test error:', error);
  }
}

// Run the test
testExtraction().then(() => {
  console.log('\n=== Test Complete ===');
  process.exit(0);
}).catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});