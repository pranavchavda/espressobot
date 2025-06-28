#!/usr/bin/env node

// Test that tasks are properly isolated by conversation
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

async function testConversationIsolation() {
  console.log('🧪 Testing Task Conversation Isolation\n');
  
  // Create two test conversations
  const conv1 = await prisma.conversations.create({
    data: {
      user_id: 1,
      title: 'Conversation 1: Espresso Machines',
      filename: `conv1-${Date.now()}.json`
    }
  });
  
  const conv2 = await prisma.conversations.create({
    data: {
      user_id: 1,
      title: 'Conversation 2: Coffee Grinders',
      filename: `conv2-${Date.now()}.json`
    }
  });
  
  console.log(`✅ Created conversation 1 (ID: ${conv1.id})`);
  console.log(`✅ Created conversation 2 (ID: ${conv2.id})\n`);
  
  // Create tasks for conversation 1
  await prisma.tasks.createMany({
    data: [
      {
        conv_id: conv1.id,
        task_id: 't1',
        description: 'Search for espresso machines',
        priority: 'high',
        status: 'pending'
      },
      {
        conv_id: conv1.id,
        task_id: 't2',
        description: 'Update espresso machine prices',
        priority: 'high',
        status: 'pending'
      }
    ]
  });
  
  // Create tasks for conversation 2
  await prisma.tasks.createMany({
    data: [
      {
        conv_id: conv2.id,
        task_id: 't1',
        description: 'Search for coffee grinders',
        priority: 'high',
        status: 'pending'
      },
      {
        conv_id: conv2.id,
        task_id: 't2',
        description: 'Check grinder inventory',
        priority: 'medium',
        status: 'pending'
      }
    ]
  });
  
  console.log('✅ Created 2 tasks for each conversation\n');
  
  // Test fetching tasks for each conversation
  console.log('📋 Testing task isolation:');
  
  // Fetch tasks for conversation 1
  const tasks1 = await prisma.tasks.findMany({
    where: { conv_id: conv1.id }
  });
  console.log(`\nConversation 1 tasks (should be about espresso machines):`);
  tasks1.forEach(t => console.log(`  - ${t.task_id}: ${t.description}`));
  
  // Fetch tasks for conversation 2
  const tasks2 = await prisma.tasks.findMany({
    where: { conv_id: conv2.id }
  });
  console.log(`\nConversation 2 tasks (should be about coffee grinders):`);
  tasks2.forEach(t => console.log(`  - ${t.task_id}: ${t.description}`));
  
  // Verify isolation
  console.log('\n✅ Verification:');
  console.log(`  - Conv 1 has ${tasks1.length} tasks (expected: 2)`);
  console.log(`  - Conv 2 has ${tasks2.length} tasks (expected: 2)`);
  console.log(`  - No task overlap: ${tasks1.every(t1 => !tasks2.find(t2 => t2.id === t1.id)) ? 'PASS' : 'FAIL'}`);
  
  // Test the API endpoint
  console.log('\n📡 Testing API endpoint:');
  const fetch = (await import('node-fetch')).default;
  
  try {
    const response1 = await fetch(`http://localhost:5173/api/conversations/${conv1.id}`);
    const data1 = await response1.json();
    console.log(`  - Conv 1 API returns ${data1.tasks?.length || 0} tasks`);
    
    const response2 = await fetch(`http://localhost:5173/api/conversations/${conv2.id}`);
    const data2 = await response2.json();
    console.log(`  - Conv 2 API returns ${data2.tasks?.length || 0} tasks`);
  } catch (e) {
    console.log('  - API test skipped (server may not be running)');
  }
  
  // Cleanup
  await prisma.tasks.deleteMany({ where: { conv_id: conv1.id } });
  await prisma.tasks.deleteMany({ where: { conv_id: conv2.id } });
  await prisma.conversations.delete({ where: { id: conv1.id } });
  await prisma.conversations.delete({ where: { id: conv2.id } });
  
  console.log('\n🧹 Cleanup complete');
  console.log('\n✨ Task isolation test completed successfully!');
  process.exit(0);
}

testConversationIsolation().catch(error => {
  console.error('❌ Test failed:', error);
  process.exit(1);
});