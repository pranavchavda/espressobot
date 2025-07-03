/**
 * Test conversation topic system
 */

import { updateConversationTopic } from '../server/tools/update-conversation-topic.js';
import pkg from '@prisma/client';
const { PrismaClient } = pkg;

const prisma = new PrismaClient();

async function testTopicSystem() {
  console.log('Testing conversation topic system...\n');
  
  try {
    // First, create a test conversation
    const testConv = await prisma.conversations.create({
      data: {
        user_id: 1,
        title: 'Test conversation for topic system',
        filename: `test-topic-${Date.now()}.json`,
        created_at: new Date(),
        updated_at: new Date()
      }
    });
    
    console.log(`Created test conversation ID: ${testConv.id}`);
    
    // Test 1: Update topic
    console.log('\nTest 1: Updating conversation topic...');
    const result = await updateConversationTopic({
      conversation_id: testConv.id.toString(),
      topic_title: 'Product Pricing Update Request',
      topic_details: 'User wants to update pricing for multiple coffee products and apply bulk discounts for the holiday season'
    });
    
    console.log('Update result:', result);
    
    // Test 2: Verify topic was saved
    console.log('\nTest 2: Verifying topic was saved...');
    const updated = await prisma.conversations.findUnique({
      where: { id: testConv.id }
    });
    
    console.log('Topic title:', updated.topic_title);
    console.log('Topic details:', updated.topic_details);
    
    // Test 3: Update topic again
    console.log('\nTest 3: Updating topic again...');
    const result2 = await updateConversationTopic({
      conversation_id: testConv.id.toString(),
      topic_title: 'Inventory Management and Preorder Setup',
      topic_details: 'Changed focus to setting up preorder products and managing inventory levels'
    });
    
    console.log('Second update result:', result2);
    
    // Clean up
    console.log('\nCleaning up test conversation...');
    await prisma.conversations.delete({
      where: { id: testConv.id }
    });
    
    console.log('\nAll tests passed! ✅');
    
  } catch (error) {
    console.error('Test failed:', error);
  } finally {
    await prisma.$disconnect();
  }
}

// Run the test
testTopicSystem();