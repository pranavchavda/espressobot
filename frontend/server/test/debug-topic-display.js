import pkg from '@prisma/client';
const { PrismaClient } = pkg;

const prisma = new PrismaClient();

async function debugTopicDisplay() {
  console.log('=== Debugging Topic Display ===\n');
  
  // Get recent conversations
  const conversations = await prisma.conversations.findMany({
    where: { user_id: 2 }, // Your user ID
    orderBy: { created_at: 'desc' },
    take: 5
  });
  
  console.log('Recent conversations:');
  conversations.forEach(conv => {
    console.log(`ID: ${conv.id}`);
    console.log(`  Title: "${conv.title}"`);
    console.log(`  Topic Title: "${conv.topic_title}"`);
    console.log(`  Has Topic: ${conv.topic_title ? 'YES' : 'NO'}`);
    console.log(`  Created: ${conv.created_at}`);
    console.log('---');
  });
  
  // Check conversation 278 specifically
  const conv278 = await prisma.conversations.findUnique({
    where: { id: 278 }
  });
  
  if (conv278) {
    console.log('\nConversation 278 (from your trace):');
    console.log(`  Title: "${conv278.title}"`);
    console.log(`  Topic Title: "${conv278.topic_title}"`);
    console.log(`  Topic Details: "${conv278.topic_details}"`);
  }
  
  await prisma.$disconnect();
}

debugTopicDisplay().catch(console.error);