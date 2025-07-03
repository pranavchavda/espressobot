import { Router } from 'express';
import { memoryOperations } from '../memory/memory-operations-local.js';
import { authenticateToken } from '../auth.js';

const router = Router();

/**
 * Get all prompt fragments with optional filtering
 */
router.get('/', authenticateToken, async (req, res) => {
  try {
    const { category, agent_type, priority, tags } = req.query;
    
    // Get all system prompt fragments
    const allFragments = await memoryOperations.getAllSystemPromptFragments();
    
    // Apply filters
    let filtered = allFragments;
    
    if (category && category !== 'all') {
      filtered = filtered.filter(f => f.metadata?.category === category);
    }
    
    if (agent_type && agent_type !== 'all') {
      filtered = filtered.filter(f => f.metadata?.agent_type === agent_type);
    }
    
    if (priority && priority !== 'all') {
      filtered = filtered.filter(f => f.metadata?.priority === priority);
    }
    
    if (tags) {
      const tagArray = Array.isArray(tags) ? tags : [tags];
      filtered = filtered.filter(f => {
        const fragmentTags = f.metadata?.tags || [];
        return tagArray.some(tag => fragmentTags.includes(tag));
      });
    }
    
    res.json({
      success: true,
      fragments: filtered,
      total: filtered.length
    });
  } catch (error) {
    console.error('Error fetching prompt fragments:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Search prompt fragments
 */
router.get('/search', authenticateToken, async (req, res) => {
  try {
    const { query, limit = 20 } = req.query;
    
    if (!query) {
      return res.status(400).json({
        success: false,
        error: 'Search query is required'
      });
    }
    
    const results = await memoryOperations.searchSystemPromptFragments(query, parseInt(limit));
    
    res.json({
      success: true,
      fragments: results,
      total: results.length
    });
  } catch (error) {
    console.error('Error searching prompt fragments:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Add a new prompt fragment
 */
router.post('/', authenticateToken, async (req, res) => {
  try {
    const { fragment, category, priority, tags, agent_type } = req.body;
    
    if (!fragment || !category) {
      return res.status(400).json({
        success: false,
        error: 'Fragment and category are required'
      });
    }
    
    const result = await memoryOperations.addSystemPromptFragment(fragment, {
      category,
      priority: priority || 'medium',
      tags: tags || [],
      agent_type: agent_type || 'all',
      created_by: req.user?.email || 'unknown',
      created_via: 'prompt-library-ui'
    });
    
    res.json({
      success: true,
      fragment: result
    });
  } catch (error) {
    console.error('Error adding prompt fragment:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Update a prompt fragment
 */
router.put('/:id', authenticateToken, async (req, res) => {
  try {
    const { id } = req.params;
    const { fragment, category, priority, tags, agent_type } = req.body;
    
    if (!fragment) {
      return res.status(400).json({
        success: false,
        error: 'Fragment content is required'
      });
    }
    
    // First update the content
    await memoryOperations.update(id, fragment);
    
    // Then update metadata by deleting and re-adding
    // (Since the memory system doesn't have direct metadata update)
    await memoryOperations.delete(id);
    
    const result = await memoryOperations.addSystemPromptFragment(fragment, {
      category: category || 'general',
      priority: priority || 'medium',
      tags: tags || [],
      agent_type: agent_type || 'all',
      updated_by: req.user?.email || 'unknown',
      updated_via: 'prompt-library-ui',
      original_id: id
    });
    
    res.json({
      success: true,
      fragment: result
    });
  } catch (error) {
    console.error('Error updating prompt fragment:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Delete a prompt fragment
 */
router.delete('/:id', authenticateToken, async (req, res) => {
  try {
    const { id } = req.params;
    
    const result = await memoryOperations.delete(id);
    
    res.json({
      success: true,
      result: result
    });
  } catch (error) {
    console.error('Error deleting prompt fragment:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Export prompt fragments
 */
router.post('/export', authenticateToken, async (req, res) => {
  try {
    const { category, agent_type } = req.body;
    
    const fragments = await memoryOperations.getAllSystemPromptFragments({
      category,
      agent_type
    });
    
    const exportData = {
      version: '1.0',
      exported_at: new Date().toISOString(),
      exported_by: req.user?.email || 'unknown',
      fragments: fragments.map(f => ({
        content: f.memory,
        metadata: f.metadata
      }))
    };
    
    res.json({
      success: true,
      data: exportData,
      count: fragments.length
    });
  } catch (error) {
    console.error('Error exporting prompt fragments:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Import prompt fragments
 */
router.post('/import', authenticateToken, async (req, res) => {
  try {
    const { data, mode = 'merge' } = req.body; // mode: 'merge' or 'replace'
    
    if (!data || !data.fragments) {
      return res.status(400).json({
        success: false,
        error: 'Invalid import data format'
      });
    }
    
    // If replace mode, clear existing fragments first
    if (mode === 'replace') {
      const existing = await memoryOperations.getAllSystemPromptFragments();
      for (const fragment of existing) {
        await memoryOperations.delete(fragment.id);
      }
    }
    
    // Import new fragments
    const results = [];
    let successCount = 0;
    let errorCount = 0;
    
    for (const item of data.fragments) {
      try {
        const result = await memoryOperations.addSystemPromptFragment(
          item.content,
          {
            ...item.metadata,
            imported_by: req.user?.email || 'unknown',
            imported_at: new Date().toISOString()
          }
        );
        results.push({ success: true, fragment: result });
        successCount++;
      } catch (error) {
        results.push({ success: false, error: error.message });
        errorCount++;
      }
    }
    
    res.json({
      success: true,
      imported: successCount,
      errors: errorCount,
      results: results
    });
  } catch (error) {
    console.error('Error importing prompt fragments:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

/**
 * Get statistics about prompt fragments
 */
router.get('/stats', authenticateToken, async (req, res) => {
  try {
    const fragments = await memoryOperations.getAllSystemPromptFragments();
    
    const stats = {
      total: fragments.length,
      by_category: {},
      by_agent_type: {},
      by_priority: {},
      recent: fragments.slice(0, 5).map(f => ({
        id: f.id,
        preview: f.memory.substring(0, 50) + '...',
        created_at: f.createdAt
      }))
    };
    
    // Count by category
    fragments.forEach(f => {
      const cat = f.metadata?.category || 'uncategorized';
      stats.by_category[cat] = (stats.by_category[cat] || 0) + 1;
      
      const agent = f.metadata?.agent_type || 'unknown';
      stats.by_agent_type[agent] = (stats.by_agent_type[agent] || 0) + 1;
      
      const priority = f.metadata?.priority || 'unknown';
      stats.by_priority[priority] = (stats.by_priority[priority] || 0) + 1;
    });
    
    res.json({
      success: true,
      stats: stats
    });
  } catch (error) {
    console.error('Error getting prompt stats:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

export default router;