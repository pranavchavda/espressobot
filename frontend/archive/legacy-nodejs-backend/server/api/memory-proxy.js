import { Router } from 'express';
import { authenticateToken } from '../auth.js';

const router = Router();

// Proxy all memory API requests to the LangGraph backend
const BACKEND_URL = process.env.LANGGRAPH_BACKEND_URL || 'http://localhost:8000';

// Admin email check middleware
const isAdmin = (req, res, next) => {
  if (req.user?.email !== 'pranav@idrinkcoffee.com') {
    return res.status(403).json({ error: 'Admin access required' });
  }
  next();
};

// Generic proxy function
async function proxyToBackend(req, res, path, method = 'GET', body = null) {
  try {
    const url = `${BACKEND_URL}/api/memory${path}`;
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': req.headers.authorization || '',
      },
    };
    
    if (body) {
      options.body = JSON.stringify(body);
    }
    
    const response = await fetch(url, options);
    const data = await response.json();
    
    if (!response.ok) {
      return res.status(response.status).json(data);
    }
    
    res.json(data);
  } catch (error) {
    console.error(`Error proxying to backend: ${error.message}`);
    res.status(500).json({ error: 'Failed to connect to backend memory service' });
  }
}

// List all memories (for admin)
router.get('/all', authenticateToken, isAdmin, async (req, res) => {
  // Default to user ID "1" for admin viewing all memories
  const userId = req.query.user_id || '1';
  const queryString = new URLSearchParams(req.query).toString();
  const path = `/list/${userId}${queryString ? '?' + queryString : ''}`;
  await proxyToBackend(req, res, path);
});

// Dashboard endpoint
router.get('/dashboard/:userId', authenticateToken, isAdmin, async (req, res) => {
  await proxyToBackend(req, res, `/dashboard/${req.params.userId}`);
});

// List memories
router.get('/list/:userId', authenticateToken, isAdmin, async (req, res) => {
  const queryString = new URLSearchParams(req.query).toString();
  const path = `/list/${req.params.userId}${queryString ? '?' + queryString : ''}`;
  await proxyToBackend(req, res, path);
});

// Search memories
router.post('/search/:userId', authenticateToken, isAdmin, async (req, res) => {
  await proxyToBackend(req, res, `/search/${req.params.userId}`, 'POST', req.body);
});

// Get single memory
router.get('/:memoryId', authenticateToken, isAdmin, async (req, res) => {
  const userId = req.query.user_id;
  const path = `/${req.params.memoryId}${userId ? '?user_id=' + userId : ''}`;
  await proxyToBackend(req, res, path);
});

// Create memory
router.post('/create/:userId', authenticateToken, isAdmin, async (req, res) => {
  await proxyToBackend(req, res, `/create/${req.params.userId}`, 'POST', req.body);
});

// Update memory
router.put('/:memoryId', authenticateToken, isAdmin, async (req, res) => {
  const userId = req.query.user_id;
  const path = `/${req.params.memoryId}${userId ? '?user_id=' + userId : ''}`;
  await proxyToBackend(req, res, path, 'PUT', req.body);
});

// Delete memory
router.delete('/:memoryId', authenticateToken, isAdmin, async (req, res) => {
  const userId = req.query.user_id;
  const path = `/${req.params.memoryId}${userId ? '?user_id=' + userId : ''}`;
  await proxyToBackend(req, res, path, 'DELETE');
});

// Bulk operations
router.post('/bulk/:userId', authenticateToken, isAdmin, async (req, res) => {
  await proxyToBackend(req, res, `/bulk/${req.params.userId}`, 'POST', req.body);
});

// Export memories
router.get('/export/:userId', authenticateToken, isAdmin, async (req, res) => {
  const queryString = new URLSearchParams(req.query).toString();
  const path = `/export/${req.params.userId}${queryString ? '?' + queryString : ''}`;
  await proxyToBackend(req, res, path);
});

// Import memories
router.post('/import/:userId', authenticateToken, isAdmin, async (req, res) => {
  // For file uploads, we need special handling
  // For now, pass the body as-is
  await proxyToBackend(req, res, `/import/${req.params.userId}`, 'POST', req.body);
});

// Cleanup old memories
router.post('/cleanup', authenticateToken, isAdmin, async (req, res) => {
  const queryString = new URLSearchParams(req.query).toString();
  const path = `/cleanup${queryString ? '?' + queryString : ''}`;
  await proxyToBackend(req, res, path, 'POST');
});

export default router;