import { Router } from 'express';
// Fix CommonJS import issue with Prisma
import pkg from '@prisma/client';
const { PrismaClient } = pkg;

const prisma = new PrismaClient();
const router = Router();

// List all conversations for the single local user (ID = 1)
router.get('/', async (req, res) => {
  const USER_ID = 1;
  const conversations = await prisma.conversations.findMany({
    where: { user_id: USER_ID },
    orderBy: { created_at: 'desc' },
  });
  res.json(conversations);
});

// Get all messages for a given conversation
router.get('/:id', async (req, res) => {
  const convId = Number(req.params.id);
  if (!convId) {
    return res.status(400).json({ error: 'Invalid conversation ID' });
  }
  const messages = await prisma.messages.findMany({
    where: { conv_id: convId },
    orderBy: { created_at: 'asc' },
  });
  const latestRun = await prisma.agent_runs.findFirst({
    where: { conv_id: convId },
    orderBy: { created_at: 'desc' },
  });
  res.json({ messages, tasks: latestRun ? JSON.parse(latestRun.tasks) : [] });
});

// Delete a conversation and its messages
router.delete('/:id', async (req, res) => {
  const convId = Number(req.params.id);
  if (!convId) {
    return res.status(400).json({ error: 'Invalid conversation ID' });
  }
  try {
    // Delete related agent_runs first
    await prisma.agent_runs.deleteMany({ where: { conv_id: convId } });
    // Then delete messages
    await prisma.messages.deleteMany({ where: { conv_id: convId } });
    // Finally delete the conversation
    await prisma.conversations.delete({ where: { id: convId } });
    res.sendStatus(204);
  } catch (error) {
    console.error('Error deleting conversation:', error);
    res.status(500).json({ error: 'Failed to delete conversation' });
  }
});

export default router;