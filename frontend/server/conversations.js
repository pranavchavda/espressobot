import { config } from 'dotenv';
config();

import { Router } from 'express';
// Fix CommonJS import issue with Prisma
import pkg from '@prisma/client';
const { PrismaClient } = pkg;
import { authenticateToken } from './auth.js';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const prisma = new PrismaClient();
const router = Router();

// List all conversations for the authenticated user
router.get('/', authenticateToken, async (req, res) => {
  // Use the authenticated user's ID, fallback to 1 for local development
  const USER_ID = req.user?.id || 1;
  const conversations = await prisma.conversations.findMany({
    where: { user_id: USER_ID },
    orderBy: { created_at: 'desc' },
  });
  res.json(conversations);
});

// Get all messages for a given conversation
router.get('/:id', authenticateToken, async (req, res) => {
  const convId = Number(req.params.id);
  const USER_ID = req.user?.id || 1;
  
  if (!convId) {
    return res.status(400).json({ error: 'Invalid conversation ID' });
  }
  
  // Verify the conversation belongs to the user
  const conversation = await prisma.conversations.findFirst({
    where: { id: convId, user_id: USER_ID }
  });
  
  if (!conversation) {
    return res.status(404).json({ error: 'Conversation not found' });
  }
  
  const messages = await prisma.messages.findMany({
    where: { conv_id: convId },
    orderBy: { created_at: 'asc' },
  });
  const latestRun = await prisma.agent_runs.findFirst({
    where: { conv_id: convId },
    orderBy: { created_at: 'desc' },
  });
  
  // Load task markdown file if it exists
  let taskMarkdown = null;
  try {
    const planPath = path.join(__dirname, 'plans', `TODO-${convId}.md`);
    const planContent = await fs.readFile(planPath, 'utf-8');
    const taskCount = (planContent.match(/^\s*-\s*\[/gm) || []).length;
    taskMarkdown = {
      markdown: planContent,
      filename: `TODO-${convId}.md`,
      taskCount: taskCount,
      conversation_id: convId
    };
  } catch (err) {
    // No task plan file, that's okay
  }
  
  res.json({ 
    messages, 
    tasks: latestRun ? JSON.parse(latestRun.tasks) : [],
    taskMarkdown: taskMarkdown
  });
});

// Delete a conversation and its messages
router.delete('/:id', authenticateToken, async (req, res) => {
  const convId = Number(req.params.id);
  const USER_ID = req.user?.id || 1;
  
  if (!convId) {
    return res.status(400).json({ error: 'Invalid conversation ID' });
  }
  
  try {
    // Verify the conversation belongs to the user
    const conversation = await prisma.conversations.findFirst({
      where: { id: convId, user_id: USER_ID }
    });
    
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation not found' });
    }
    
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