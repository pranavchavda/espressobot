import { PrismaClient } from '@prisma/client';
import dotenv from 'dotenv';

dotenv.config();

console.log('DATABASE_URL:', process.env.DATABASE_URL);

const prisma = new PrismaClient({
  log: ['query', 'info', 'warn', 'error'],
});

async function testConnection() {
  try {
    const users = await prisma.users.findMany();
    console.log('✅ Database connected! Found', users.length, 'users');
    process.exit(0);
  } catch (error) {
    console.error('❌ Database connection failed:', error);
    process.exit(1);
  }
}

testConnection();