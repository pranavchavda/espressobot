import { config } from 'dotenv';
config();

import pkg from '@prisma/client';
const { PrismaClient } = pkg;

const prisma = new PrismaClient();

async function main() {
  // Create default user
  const user = await prisma.users.upsert({
    where: { id: 1 },
    update: {},
    create: {
      id: 1,
      email: 'user@example.com',
      password_hash: 'placeholder',
      name: 'Default User',
      bio: 'Local development user',
      is_whitelisted: true,
      created_at: new Date(),
    },
  });
  
  console.log('Created default user:', user);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });