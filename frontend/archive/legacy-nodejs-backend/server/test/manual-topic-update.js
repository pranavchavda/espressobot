import pkg from '@prisma/client';
const { PrismaClient } = pkg;

const prisma = new PrismaClient();

async function manualTopicUpdate() {
  console.log('=== Manual Topic Update Test ===\n');
  
  // Update conversation 279 directly in database
  const updated = await prisma.conversations.update({
    where: { id: 279 },
    data: {
      topic_title: 'MANUAL UPDATE: Topic Display Fixed!',
      topic_details: 'This was updated manually to test if the sidebar refreshes',
      updated_at: new Date()
    }
  });
  
  console.log('Updated conversation:', {
    id: updated.id,
    title: updated.title,
    topic_title: updated.topic_title,
    topic_details: updated.topic_details
  });
  
  console.log('\nNow refresh the browser to see if the sidebar updates!');
  
  await prisma.$disconnect();
}

manualTopicUpdate().catch(console.error);