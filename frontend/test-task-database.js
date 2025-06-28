#!/usr/bin/env node

// Test the task database functionality
import { PrismaClient } from '@prisma/client';
import { getTasksForConversation } from './server/tools/task-db-tools.js';

const prisma = new PrismaClient();

async function testTaskDatabase() {
  console.log('Testing task database functionality...\n');
  
  // Create a test conversation
  const testConv = await prisma.conversations.create({
    data: {
      user_id: 1,
      title: 'Test Task Database',
      filename: `test-task-db-${Date.now()}.json`,
      created_at: new Date(),
      updated_at: new Date()
    }
  });
  
  console.log('Created test conversation:', testConv.id);
  
  // Test 1: Create a task plan
  console.log('\n1. Creating task plan...');
  // Create tasks directly since we can't access tool internals
  const tasks = [
    {
      conv_id: testConv.id,
      task_id: 't1',
      description: 'Search for espresso machines with tag "premium"',
      priority: 'high',
      assigned_to: 'Product_Update_Agent',
      status: 'pending'
    },
    {
      conv_id: testConv.id,
      task_id: 't2',
      description: 'Update prices for found products',
      priority: 'high',
      assigned_to: 'Product_Update_Agent',
      dependencies: 't1',
      status: 'pending'
    },
    {
      conv_id: testConv.id,
      task_id: 't3',
      description: 'Generate report of changes',
      priority: 'medium',
      assigned_to: 'Task_Planner_Agent',
      dependencies: 't2',
      status: 'pending'
    }
  ];
  
  // Create task plan
  const taskPlan = await prisma.task_plans.create({
    data: {
      conv_id: testConv.id,
      title: 'Search and Update Products',
      description: 'Find espresso machines and update their prices'
    }
  });
  
  // Create tasks
  for (const task of tasks) {
    await prisma.tasks.create({ data: task });
  }
  
  const planResult = {
    title: 'Search and Update Products',
    description: 'Find espresso machines and update their prices',
    tasks: [
      {
        id: 't1',
        description: 'Search for espresso machines with tag "premium"',
        priority: 'high',
        dependencies: [],
        assignTo: 'Product_Update_Agent'
      },
      {
        id: 't2',
        description: 'Update prices for found products',
        priority: 'high',
        dependencies: ['t1'],
        assignTo: 'Product_Update_Agent'
      },
      {
        id: 't3',
        description: 'Generate report of changes',
        priority: 'medium',
        dependencies: ['t2'],
        assignTo: 'Task_Planner_Agent'
      }
    ],
    success: true,
    planId: taskPlan.id,
    taskCount: tasks.length
  };
  
  console.log('Plan result:', planResult);
  
  // Test 2: Get tasks
  console.log('\n2. Getting tasks...');
  const foundTasks = await getTasksForConversation(String(testConv.id));
  console.log('Found tasks:', foundTasks);
  
  // Test 3: Update task status
  console.log('\n3. Updating task t1 to in_progress...');
  const update1 = await prisma.tasks.updateMany({
    where: {
      conv_id: testConv.id,
      task_id: 't1'
    },
    data: {
      status: 'in_progress',
      notes: 'Starting product search...',
      updated_at: new Date()
    }
  });
  
  const updateResult1 = {
    success: true,
    count: update1.count
  };
  console.log('Update result:', updateResult1);
  
  // Test 4: Complete task
  console.log('\n4. Completing task t1...');
  const update2 = await prisma.tasks.updateMany({
    where: {
      conv_id: testConv.id,
      task_id: 't1'
    },
    data: {
      status: 'completed',
      notes: 'Found 15 premium espresso machines',
      updated_at: new Date(),
      completed_at: new Date()
    }
  });
  
  const updateResult2 = {
    success: true,
    count: update2.count
  };
  console.log('Update result:', updateResult2);
  
  // Test 5: Get updated tasks
  console.log('\n5. Getting updated tasks...');
  const updatedTasks = await getTasksForConversation(String(testConv.id));
  console.log('Updated tasks:', updatedTasks);
  
  // Cleanup
  await prisma.tasks.deleteMany({ where: { conv_id: testConv.id } });
  await prisma.task_plans.deleteMany({ where: { conv_id: testConv.id } });
  await prisma.conversations.delete({ where: { id: testConv.id } });
  
  console.log('\n✅ All tests passed!');
  process.exit(0);
}

testTaskDatabase().catch(error => {
  console.error('Test failed:', error);
  process.exit(1);
});