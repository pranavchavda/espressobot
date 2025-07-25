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
    taskMarkdown: taskMarkdown,
    topic_title: conversation.topic_title,
    topic_details: conversation.topic_details
  });
});

// Update conversation topic
router.put('/:id/topic', authenticateToken, async (req, res) => {
  const convId = Number(req.params.id);
  const { topic_title, topic_details } = req.body;
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
    
    // Update the topic
    const updated = await prisma.conversations.update({
      where: { id: convId },
      data: {
        topic_title,
        topic_details,
        updated_at: new Date()
      }
    });
    
    res.json({
      success: true,
      conversation: updated
    });
  } catch (error) {
    console.error('Error updating conversation topic:', error);
    res.status(500).json({ error: 'Failed to update conversation topic' });
  }
});

// Edit a message and optionally re-process conversation from that point
router.put('/:convId/messages/:msgId', authenticateToken, async (req, res) => {
  const convId = Number(req.params.convId);
  const msgId = Number(req.params.msgId);
  const { content, reprocess = true } = req.body;
  const USER_ID = req.user?.id || 1;
  
  if (!convId || !msgId) {
    return res.status(400).json({ error: 'Invalid conversation or message ID' });
  }
  
  if (!content || content.trim() === '') {
    return res.status(400).json({ error: 'Content cannot be empty' });
  }
  
  try {
    // Verify the conversation belongs to the user
    const conversation = await prisma.conversations.findFirst({
      where: { id: convId, user_id: USER_ID }
    });
    
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation not found' });
    }
    
    // Get the message to edit
    const message = await prisma.messages.findFirst({
      where: { id: msgId, conv_id: convId }
    });
    
    if (!message) {
      return res.status(404).json({ error: 'Message not found' });
    }
    
    // Update the message with edit tracking
    const updatedMessage = await prisma.messages.update({
      where: { id: msgId },
      data: {
        original_content: message.original_content || message.content, // Preserve original
        content: content,
        edited_at: new Date()
      }
    });
    
    // If reprocess is true, delete all messages after this one
    if (reprocess) {
      // Get the timestamp of the edited message
      const editedMsgTime = message.created_at;
      
      // Delete all messages after the edited message
      await prisma.messages.deleteMany({
        where: {
          conv_id: convId,
          created_at: { gt: editedMsgTime }
        }
      });
      
      // Also delete any agent_runs created after this message
      await prisma.agent_runs.deleteMany({
        where: {
          conv_id: convId,
          created_at: { gt: editedMsgTime }
        }
      });
    }
    
    res.json({
      success: true,
      message: updatedMessage,
      reprocessed: reprocess
    });
  } catch (error) {
    console.error('Error editing message:', error);
    res.status(500).json({ error: 'Failed to edit message' });
  }
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