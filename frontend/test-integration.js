#!/usr/bin/env node

// Integration test for real-time task updates
import { PrismaClient } from '@prisma/client';
import fetch from 'node-fetch';

const prisma = new PrismaClient();

async function simulateTaskProgress() {
  console.log('🧪 Integration Test: Real-time Task Updates\n');
  
  // Create a test conversation
  const conv = await prisma.conversations.create({
    data: {
      user_id: 1,
      title: 'Test Real-time Tasks',
      filename: `test-realtime-${Date.now()}.json`
    }
  });
  
  console.log(`✅ Created conversation ${conv.id}\n`);
  
  // Create a task plan
  const plan = await prisma.task_plans.create({
    data: {
      conv_id: conv.id,
      title: 'Search and Update Products',
      description: 'Find top espresso machines and update descriptions'
    }
  });
  
  // Create tasks
  const tasks = [
    {
      conv_id: conv.id,
      task_id: 't1',
      description: 'Search for top 3 espresso machines',
      priority: 'high',
      assigned_to: 'Product_Update_Agent',
      status: 'pending'
    },
    {
      conv_id: conv.id,
      task_id: 't2',
      description: 'Update product descriptions',
      priority: 'high',
      assigned_to: 'Product_Update_Agent',
      dependencies: 't1',
      status: 'pending'
    },
    {
      conv_id: conv.id,
      task_id: 't3',
      description: 'Generate summary report',
      priority: 'medium',
      assigned_to: 'Task_Planner_Agent',
      dependencies: 't2',
      status: 'pending'
    }
  ];
  
  for (const task of tasks) {
    await prisma.tasks.create({ data: task });
  }
  
  console.log('✅ Created 3 tasks\n');
  console.log('📋 Initial Task Status:');
  await showTasks(conv.id);
  
  // Simulate agent working on tasks
  console.log('\n🤖 Simulating agent progress...\n');
  
  // Start task 1
  await new Promise(resolve => setTimeout(resolve, 1000));
  await prisma.tasks.updateMany({
    where: { conv_id: conv.id, task_id: 't1' },
    data: { 
      status: 'in_progress',
      notes: 'Searching product catalog...',
      updated_at: new Date()
    }
  });
  console.log('⏳ Task t1: in_progress - Searching product catalog...');
  
  // Complete task 1
  await new Promise(resolve => setTimeout(resolve, 2000));
  await prisma.tasks.updateMany({
    where: { conv_id: conv.id, task_id: 't1' },
    data: { 
      status: 'completed',
      notes: 'Found 3 premium espresso machines',
      completed_at: new Date(),
      updated_at: new Date()
    }
  });
  console.log('✅ Task t1: completed - Found 3 premium espresso machines');
  
  // Start task 2
  await new Promise(resolve => setTimeout(resolve, 500));
  await prisma.tasks.updateMany({
    where: { conv_id: conv.id, task_id: 't2' },
    data: { 
      status: 'in_progress',
      notes: 'Updating descriptions for 3 products...',
      updated_at: new Date()
    }
  });
  console.log('⏳ Task t2: in_progress - Updating descriptions for 3 products...');
  
  // Complete task 2
  await new Promise(resolve => setTimeout(resolve, 2000));
  await prisma.tasks.updateMany({
    where: { conv_id: conv.id, task_id: 't2' },
    data: { 
      status: 'completed',
      notes: 'Updated all product descriptions',
      completed_at: new Date(),
      updated_at: new Date()
    }
  });
  console.log('✅ Task t2: completed - Updated all product descriptions');
  
  // Start and complete task 3
  await new Promise(resolve => setTimeout(resolve, 500));
  await prisma.tasks.updateMany({
    where: { conv_id: conv.id, task_id: 't3' },
    data: { 
      status: 'in_progress',
      notes: 'Generating report...',
      updated_at: new Date()
    }
  });
  console.log('⏳ Task t3: in_progress - Generating report...');
  
  await new Promise(resolve => setTimeout(resolve, 1000));
  await prisma.tasks.updateMany({
    where: { conv_id: conv.id, task_id: 't3' },
    data: { 
      status: 'completed',
      notes: 'Report generated: 3 products updated successfully',
      completed_at: new Date(),
      updated_at: new Date()
    }
  });
  console.log('✅ Task t3: completed - Report generated: 3 products updated successfully');
  
  console.log('\n📋 Final Task Status:');
  await showTasks(conv.id);
  
  // Cleanup
  await prisma.tasks.deleteMany({ where: { conv_id: conv.id } });
  await prisma.task_plans.deleteMany({ where: { conv_id: conv.id } });
  await prisma.conversations.delete({ where: { id: conv.id } });
  
  console.log('\n🧹 Cleanup complete');
  console.log('\n✨ Integration test completed successfully!');
  console.log('\nIn a real scenario, the multi-agent orchestrator would:');
  console.log('1. Poll the database every 500ms for task changes');
  console.log('2. Send SSE events with task updates');
  console.log('3. Frontend would display real-time progress');
  
  process.exit(0);
}

async function showTasks(convId) {
  const tasks = await prisma.tasks.findMany({
    where: { conv_id: convId },
    orderBy: { task_id: 'asc' }
  });
  
  for (const task of tasks) {
    const status = task.status === 'completed' ? '✅' : 
                   task.status === 'in_progress' ? '⏳' : 
                   task.status === 'blocked' ? '🚫' : '⭕';
    console.log(`  ${status} ${task.task_id}: ${task.description}`);
    if (task.notes) {
      console.log(`     └─ ${task.notes}`);
    }
  }
}

simulateTaskProgress().catch(error => {
  console.error('❌ Test failed:', error);
  process.exit(1);
});