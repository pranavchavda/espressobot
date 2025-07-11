import { Router } from 'express';
import { authenticateToken } from './auth.js';

const router = Router();

// Check Google Tasks authorization status
router.get('/auth_status', authenticateToken, (req, res) => {
  // For now, return not authorized since Google Tasks integration is not implemented
  res.json({ is_authorized: false });
});

// Get task lists
router.get('/lists', authenticateToken, (req, res) => {
  res.status(501).json({ 
    error: 'Google Tasks integration is not configured',
    message: 'This feature requires Google Tasks API setup'
  });
});

// Get tasks
router.get('/', authenticateToken, (req, res) => {
  res.status(501).json({ 
    error: 'Google Tasks integration is not configured',
    message: 'This feature requires Google Tasks API setup'
  });
});

// Create task
router.post('/', authenticateToken, (req, res) => {
  res.status(501).json({ 
    error: 'Google Tasks integration is not configured',
    message: 'This feature requires Google Tasks API setup'
  });
});

// Update task
router.put('/:taskId', authenticateToken, (req, res) => {
  res.status(501).json({ 
    error: 'Google Tasks integration is not configured',
    message: 'This feature requires Google Tasks API setup'
  });
});

// Complete task
router.post('/:taskId/complete', authenticateToken, (req, res) => {
  res.status(501).json({ 
    error: 'Google Tasks integration is not configured',
    message: 'This feature requires Google Tasks API setup'
  });
});

// Delete task
router.delete('/:taskId', authenticateToken, (req, res) => {
  res.status(501).json({ 
    error: 'Google Tasks integration is not configured',
    message: 'This feature requires Google Tasks API setup'
  });
});

// Google OAuth authorization endpoint placeholder
router.get('/authorize/google', (req, res) => {
  res.status(501).json({ 
    error: 'Google Tasks OAuth is not configured',
    message: 'This feature requires Google Tasks API and OAuth setup'
  });
});

export default router;