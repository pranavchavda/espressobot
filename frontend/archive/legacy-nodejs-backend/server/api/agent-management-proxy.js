/**
 * Agent Management Proxy
 * Proxies agent management requests to the Python LangGraph backend
 */

import express from 'express';

const router = express.Router();

// Python backend URL
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

/**
 * Proxy all agent management requests to Python backend
 */
router.all('*', async (req, res) => {
  try {
    const path = req.originalUrl.replace('/api/agent-management', '/api/agent-management');
    const url = `${PYTHON_BACKEND_URL}${path}`;
    
    console.log(`[Agent Management Proxy] ${req.method} ${url}`);
    console.log(`[Agent Management Proxy] Body:`, req.body);
    
    // Prepare request options
    const options = {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    };
    
    // Add body for POST/PUT requests
    if (req.method !== 'GET' && req.method !== 'HEAD' && req.body) {
      // Express should have already parsed the JSON
      options.body = JSON.stringify(req.body);
      console.log(`[Agent Management Proxy] Sending body:`, options.body);
    }
    
    // Make request to Python backend
    const response = await fetch(url, options);
    
    // Check if response is ok before trying to parse JSON
    if (!response.ok) {
      console.log(`[Agent Management Proxy] Response status: ${response.status}`);
      const text = await response.text();
      console.log(`[Agent Management Proxy] Response text:`, text);
      
      // Try to parse as JSON, otherwise return as text
      try {
        const data = JSON.parse(text);
        res.status(response.status).json(data);
      } catch {
        res.status(response.status).json({ error: text });
      }
      return;
    }
    
    const data = await response.json();
    
    // Return response
    res.status(response.status).json(data);
    
  } catch (error) {
    console.error('[Agent Management Proxy] Error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to proxy request to backend'
    });
  }
});

export default router;