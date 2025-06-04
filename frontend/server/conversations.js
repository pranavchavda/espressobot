import { Router } from 'express';
import { PrismaClient } from '@prisma/client';

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
  await prisma.messages.deleteMany({ where: { conv_id: convId } });
  await prisma.conversations.delete({ where: { id: convId } });
  res.sendStatus(204);
});

export default router;