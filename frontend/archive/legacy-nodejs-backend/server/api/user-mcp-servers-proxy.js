/**
 * User MCP Servers Proxy
 * Proxies MCP server management requests to the Python LangGraph backend
 */

import express from 'express';

const router = express.Router();

// Python backend URL
const PYTHON_BACKEND_URL = process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';

/**
 * Proxy all MCP server requests to Python backend
 */
router.all('*', async (req, res) => {
  try {
    const path = req.originalUrl.replace('/api/user-mcp-servers', '/api/user-mcp-servers');
    const url = `${PYTHON_BACKEND_URL}${path}`;
    
    console.log(`[MCP Servers Proxy] ${req.method} ${url}`);
    
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
      options.body = JSON.stringify(req.body);
    }
    
    // Make request to Python backend
    const response = await fetch(url, options);
    
    // Check if response is ok before trying to parse JSON
    if (!response.ok) {
      const text = await response.text();
      
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
    console.error('[MCP Servers Proxy] Error:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to proxy request to backend'
    });
  }
});

export default router;