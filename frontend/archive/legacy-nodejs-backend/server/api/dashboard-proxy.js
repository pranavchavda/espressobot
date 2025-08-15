/**
 * Dashboard Proxy API
 * Proxies dashboard requests to the Python backend
 */

import { Router } from 'express';
import { authenticateToken } from '../auth.js';

const router = Router();

// Python backend URL
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

/**
 * Proxy function to forward requests to Python backend
 */
async function proxyToPython(endpoint, query = {}) {
  try {
    const queryString = new URLSearchParams(query).toString();
    const url = `${PYTHON_BACKEND_URL}/api/dashboard/${endpoint}${queryString ? `?${queryString}` : ''}`;
    
    console.log(`[Dashboard Proxy] Forwarding to: ${url}`);
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });

    if (!response.ok) {
      console.error(`[Dashboard Proxy] Python backend error: ${response.status} ${response.statusText}`);
      const errorText = await response.text();
      console.error(`[Dashboard Proxy] Error details:`, errorText);
      throw new Error(`Backend returned ${response.status}: ${errorText}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`[Dashboard Proxy] Error calling Python backend:`, error);
    throw error;
  }
}

/**
 * GET /api/dashboard/analytics
 * Proxy to Python backend analytics endpoint
 */
router.get('/analytics', authenticateToken, async (req, res) => {
  try {
    const { start_date, end_date } = req.query;
    const userId = req.user?.id || '1';
    
    // Ensure dates are strings, not objects
    let startDate = start_date;
    let endDate = end_date;
    
    // Handle if dates come as objects or invalid formats
    if (typeof startDate === 'object') {
      startDate = startDate.toString();
    }
    if (typeof endDate === 'object') {
      endDate = endDate.toString();
    }
    
    // Default to today if not provided or invalid
    if (!startDate || startDate === '[object Object]') {
      startDate = new Date().toISOString().split('T')[0];
    }
    if (!endDate || endDate === '[object Object]') {
      endDate = new Date().toISOString().split('T')[0];
    }
    
    console.log(`[Dashboard Proxy] Analytics request: start=${startDate}, end=${endDate}, user=${userId}`);
    
    const data = await proxyToPython('analytics', {
      start_date: startDate,
      end_date: endDate,
      user_id: userId
    });
    
    res.json(data);
  } catch (error) {
    console.error('[Dashboard Proxy] Analytics error:', error);
    res.status(500).json({ 
      error: 'Failed to fetch analytics data',
      details: error.message 
    });
  }
});

/**
 * GET /api/dashboard/summary
 * Proxy to Python backend summary endpoint
 */
router.get('/summary', authenticateToken, async (req, res) => {
  try {
    const { date } = req.query;
    const userId = req.user?.id || '1';
    
    console.log(`[Dashboard Proxy] Summary request: date=${date}, user=${userId}`);
    
    const data = await proxyToPython('summary', {
      date: date || new Date().toISOString().split('T')[0],
      user_id: userId
    });
    
    res.json(data);
  } catch (error) {
    console.error('[Dashboard Proxy] Summary error:', error);
    res.status(500).json({ 
      error: 'Failed to fetch summary data',
      details: error.message 
    });
  }
});

/**
 * GET /api/dashboard/stats
 * Proxy to Python backend stats endpoint
 */
router.get('/stats', authenticateToken, async (req, res) => {
  try {
    console.log(`[Dashboard Proxy] Stats request`);
    
    const data = await proxyToPython('stats');
    
    res.json(data);
  } catch (error) {
    console.error('[Dashboard Proxy] Stats error:', error);
    res.status(500).json({ 
      error: 'Failed to fetch stats data',
      details: error.message 
    });
  }
});

/**
 * GET /api/dashboard/activity
 * Proxy to Python backend activity endpoint
 */
router.get('/activity', authenticateToken, async (req, res) => {
  try {
    const { days } = req.query;
    
    console.log(`[Dashboard Proxy] Activity request: days=${days}`);
    
    const data = await proxyToPython('activity', {
      days: days || 7
    });
    
    res.json(data);
  } catch (error) {
    console.error('[Dashboard Proxy] Activity error:', error);
    res.status(500).json({ 
      error: 'Failed to fetch activity data',
      details: error.message 
    });
  }
});

export default router;