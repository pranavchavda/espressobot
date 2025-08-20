/**
 * Price Monitor Proxy API
 * Proxies all price monitor requests to the Python backend
 */

import { Router } from 'express';
import { authenticateToken } from '../auth.js';

const router = Router();

// Python backend URL
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

/**
 * Generic proxy handler for all price monitor routes
 */
router.all('*', authenticateToken, async (req, res) => {
  try {
    // Get the path after /api/price-monitor
    const path = req.path;
    const method = req.method;
    
    // Build the backend URL
    const url = `${PYTHON_BACKEND_URL}/api/price-monitor${path}`;
    
    console.log(`[Price Monitor Proxy] ${method} ${url}`);
    
    // Prepare fetch options
    const fetchOptions = {
      method: method,
      headers: {
        'Content-Type': 'application/json',
      }
    };
    
    // Add query parameters for GET requests
    if (method === 'GET') {
      const queryString = new URLSearchParams(req.query).toString();
      if (queryString) {
        fetchOptions.url = `${url}?${queryString}`;
      }
    }
    
    // Add body for POST/PUT/PATCH requests
    if (['POST', 'PUT', 'PATCH'].includes(method) && req.body) {
      fetchOptions.body = JSON.stringify(req.body);
    }
    
    // Make the request to Python backend
    const response = await fetch(fetchOptions.url || url, fetchOptions);
    
    // Get response data
    let data;
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }
    
    // Forward the response status and data
    res.status(response.status);
    
    if (typeof data === 'object') {
      res.json(data);
    } else {
      res.send(data);
    }
    
  } catch (error) {
    console.error('[Price Monitor Proxy] Error:', error);
    res.status(500).json({ 
      error: 'Failed to proxy request to Python backend',
      details: error.message,
      path: req.path,
      method: req.method
    });
  }
});

export default router;