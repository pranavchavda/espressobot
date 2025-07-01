import { Router } from 'express';
import { authenticateToken } from './auth.js';
import { simpleLocalMemory } from './memory/simple-local-memory.js';

const router = Router();

// Admin email check middleware
const isAdmin = (req, res, next) => {
  if (req.user?.email !== 'pranav@idrinkcoffee.com') {
    return res.status(403).json({ error: 'Admin access required' });
  }
  next();
};

// Get all memories with optional pagination
router.get('/all', authenticateToken, isAdmin, async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 100;
    const userId = req.query.userId || null;
    
    // Get all memories from the database
    const memories = await simpleLocalMemory.getAll(userId, limit);
    
    // Get statistics
    const stats = simpleLocalMemory.getStats();
    
    res.json({
      memories,
      stats,
      total: stats.total
    });
  } catch (error) {
    console.error('Error fetching memories:', error);
    res.status(500).json({ error: 'Failed to fetch memories' });
  }
});

// Search memories
router.get('/search', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { q: query, userId, limit = 20 } = req.query;
    
    if (!query) {
      return res.status(400).json({ error: 'Query parameter required' });
    }
    
    const memories = await simpleLocalMemory.search(query, userId, parseInt(limit));
    
    res.json({
      memories,
      query,
      count: memories.length
    });
  } catch (error) {
    console.error('Error searching memories:', error);
    res.status(500).json({ error: 'Failed to search memories' });
  }
});

// Get memory statistics
router.get('/stats', authenticateToken, isAdmin, async (req, res) => {
  try {
    const stats = simpleLocalMemory.getStats();
    res.json(stats);
  } catch (error) {
    console.error('Error getting memory stats:', error);
    res.status(500).json({ error: 'Failed to get memory statistics' });
  }
});

// Update a memory
router.put('/:id', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const { content } = req.body;
    
    if (!content) {
      return res.status(400).json({ error: 'Content is required' });
    }
    
    const result = await simpleLocalMemory.update(id, content);
    res.json(result);
  } catch (error) {
    console.error('Error updating memory:', error);
    res.status(500).json({ error: 'Failed to update memory' });
  }
});

// Delete a memory
router.delete('/:id', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { id } = req.params;
    const result = await simpleLocalMemory.delete(id);
    res.json(result);
  } catch (error) {
    console.error('Error deleting memory:', error);
    res.status(500).json({ error: 'Failed to delete memory' });
  }
});

// Delete all memories for a user
router.delete('/user/:userId', authenticateToken, isAdmin, async (req, res) => {
  try {
    const { userId } = req.params;
    const result = await simpleLocalMemory.deleteAll(userId);
    res.json(result);
  } catch (error) {
    console.error('Error deleting user memories:', error);
    res.status(500).json({ error: 'Failed to delete user memories' });
  }
});

// Get all unique user IDs that have memories
router.get('/users', authenticateToken, isAdmin, async (req, res) => {
  try {
    const stats = simpleLocalMemory.getStats();
    const users = stats.byUser.map(u => ({
      userId: u.user_id,
      memoryCount: u.count
    }));
    res.json({ users });
  } catch (error) {
    console.error('Error getting users with memories:', error);
    res.status(500).json({ error: 'Failed to get users list' });
  }
});

export default router;