#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';

const client = new PrismaClient();

async function testConnection() {
  try {
    console.log('🔍 Testing database connection...');
    
    // Test basic connection
    const result = await client.$queryRaw`SELECT version()`;
    console.log('✅ Database connected successfully!');
    console.log('📊 Database version:', result[0].version);
    
    // Test if it's PostgreSQL
    if (result[0].version.includes('PostgreSQL')) {
      console.log('✅ Confirmed: Using PostgreSQL database');
    } else {
      console.log('❌ Warning: Not using PostgreSQL');
    }
    
    // Test a simple query
    const userCount = await client.users.count();
    console.log(`👥 User count: ${userCount}`);
    
    const conversationCount = await client.conversations.count();
    console.log(`💬 Conversation count: ${conversationCount}`);
    
    const messageCount = await client.messages.count();
    console.log(`📝 Message count: ${messageCount}`);
    
    console.log('🎉 All database operations working correctly!');
    
  } catch (error) {
    console.error('❌ Database connection failed:', error.message);
  } finally {
    await client.$disconnect();
  }
}

testConnection();