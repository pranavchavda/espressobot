#!/usr/bin/env node
/**
 * Test improved memory extraction with 2 facts per exchange
 */

import { memoryOperations } from './server/memory/memory-operations-local.js';

// Test long conversation with multiple exchanges
const longConversation = `User: Hi, my name is Pranav and I work as a generalist at iDrinkCoffee.com. I'm working on two chatbot projects.
Assistant: Hello Pranav! It's great to meet you. I understand you're a generalist at iDrinkCoffee.com working on chatbot projects. Could you tell me more about these chatbots?

User: Sure! The first one is Bruno, which is a customer support chatbot. The second is Espressobot, which helps with store management. Remember that Bruno handles customer inquiries.
Assistant: I've noted that Bruno is your customer support chatbot that handles customer inquiries, and Espressobot helps with store management. These sound like valuable tools for iDrinkCoffee.com!

User: Yes exactly. Also, please remember that I prefer to review all changes before they're applied to production. My favorite coffee is Ethiopian Yirgacheffe.
Assistant: I'll remember your preferences: you prefer to review all changes before production deployment, and your favorite coffee is Ethiopian Yirgacheffe. Is there anything specific about these chatbots you'd like help with?

User: Actually, the CEO of our company is Slawek Janicki. Can you help me document the requirements?
Assistant: I've noted that Slawek Janicki is the CEO of iDrinkCoffee.com. I'd be happy to help you document the requirements for both Bruno and Espressobot.`;

// Test explicit remember request
const rememberConversation = `User: I want to update our pricing strategy. Remember this: we offer 15% discounts on all combo products and 20% on bulk orders over $500.
Assistant: I've remembered your pricing strategy: 15% discounts on combo products and 20% discounts on bulk orders over $500. Would you like me to help implement these discount rules?`;

// Test with system/metric content that should be filtered
const systemContentTest = `User: What's the status of my memory?
Assistant: {"type":"context_usage","responseTime":0,"timestamp":"2025-07-01T20:28:21.347Z"}`;

async function testImprovedExtraction() {
  console.log('=== Testing Improved Memory Extraction ===\n');
  
  try {
    // Test 1: Long conversation with multiple exchanges
    console.log('Test 1: Long conversation extraction...');
    const facts1 = await memoryOperations.extractMemorySummary(longConversation, {
      conversationId: 'test-long',
      agent: 'test'
    });
    
    console.log(`\nExtracted ${facts1.length} facts from long conversation:`);
    facts1.forEach((fact, i) => {
      console.log(`${i + 1}. ${fact.content}`);
    });
    
    // Test 2: Explicit remember request
    console.log('\n\nTest 2: Explicit remember request...');
    const facts2 = await memoryOperations.extractMemorySummary(rememberConversation, {
      conversationId: 'test-remember',
      agent: 'test'
    });
    
    console.log(`\nExtracted ${facts2.length} facts from remember request:`);
    facts2.forEach((fact, i) => {
      console.log(`${i + 1}. ${fact.content}`);
    });
    
    // Test 3: System content (should extract nothing)
    console.log('\n\nTest 3: System content filtering...');
    const facts3 = await memoryOperations.extractMemorySummary(systemContentTest, {
      conversationId: 'test-system',
      agent: 'test'
    });
    
    console.log(`\nExtracted ${facts3.length} facts from system content (should be 0 or minimal)`);
    
    // Test actual storage with deduplication
    console.log('\n\nTest 4: Storage with deduplication...');
    const userId = 'test_improved';
    
    // Store facts from long conversation
    let stored = 0;
    let duplicates = 0;
    
    for (const fact of facts1) {
      const result = await memoryOperations.add(fact.content, userId, fact.metadata);
      if (result.success) {
        stored++;
      } else if (result.reason === 'duplicate' || result.reason === 'semantic_match') {
        duplicates++;
        console.log(`Duplicate detected: "${fact.content.substring(0, 50)}..."`);
      }
    }
    
    console.log(`\nStored ${stored} facts, rejected ${duplicates} duplicates`);
    
    // Show final stored memories
    const allMemories = await memoryOperations.getAll(userId, 20);
    console.log(`\n=== Final Stored Memories (${allMemories.length}) ===`);
    allMemories.forEach((mem, i) => {
      console.log(`${i + 1}. ${mem.memory}`);
    });
    
    // Clean up
    await memoryOperations.deleteAll(userId);
    console.log('\n✅ Test data cleaned up');
    
  } catch (error) {
    console.error('Test error:', error);
  }
}

// Run the test
testImprovedExtraction().then(() => {
  console.log('\n=== Test Complete ===');
  process.exit(0);
}).catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});