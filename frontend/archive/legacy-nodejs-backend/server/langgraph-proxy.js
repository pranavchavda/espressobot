/**
 * Proxy for LangGraph Backend
 * Forwards requests from the frontend to the new LangGraph backend
 */

import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';

const router = express.Router();

// Get backend URL from environment or use default
const LANGGRAPH_BACKEND_URL = process.env.LANGGRAPH_BACKEND_URL || 'http://localhost:8000';

console.log(`🔗 Proxying to LangGraph backend at: ${LANGGRAPH_BACKEND_URL}`);

// Create proxy middleware for streaming endpoint
const sseProxy = createProxyMiddleware({
  target: LANGGRAPH_BACKEND_URL,
  changeOrigin: true,
  pathRewrite: {
    '^/api/agent/run': '/api/agent/stream'  // Rewrite /run to /stream
  },
  onProxyReq: (proxyReq, req, res) => {
    // Log the request being proxied
    console.log(`[LangGraph Proxy] ${req.method} ${req.path} -> ${LANGGRAPH_BACKEND_URL}/api/agent/stream`);
    
    // Forward the body for POST requests
    if (req.body) {
      const bodyData = JSON.stringify(req.body);
      proxyReq.setHeader('Content-Type', 'application/json');
      proxyReq.setHeader('Content-Length', Buffer.byteLength(bodyData));
      proxyReq.write(bodyData);
    }
  },
  onProxyRes: (proxyRes, req, res) => {
    // Set headers for NDJSON streaming
    res.setHeader('Content-Type', 'application/x-ndjson');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('X-Accel-Buffering', 'no');
  },
  onError: (err, req, res) => {
    console.error('[LangGraph Proxy] Error:', err);
    res.status(502).json({
      error: 'Backend connection failed',
      message: err.message,
      backend: LANGGRAPH_BACKEND_URL
    });
  }
});

// Create proxy for other endpoints
const generalProxy = createProxyMiddleware({
  target: LANGGRAPH_BACKEND_URL,
  changeOrigin: true,
  onProxyReq: (proxyReq, req, res) => {
    console.log(`[LangGraph Proxy] ${req.method} ${req.path} -> ${LANGGRAPH_BACKEND_URL}${req.path}`);
  },
  onError: (err, req, res) => {
    console.error('[LangGraph Proxy] Error:', err);
    res.status(502).json({
      error: 'Backend connection failed',
      message: err.message,
      backend: LANGGRAPH_BACKEND_URL
    });
  }
});

// Route /api/agent/run to SSE endpoint
router.post('/run', sseProxy);

// Route other agent endpoints
router.use('/message', generalProxy);
router.use('/approve', generalProxy);
router.use('/reject', generalProxy);
router.use('/interrupt', generalProxy);
router.use('/logs', generalProxy);
router.use('/agents', generalProxy);

// Health check for the backend
router.get('/health', async (req, res) => {
  try {
    const response = await fetch(`${LANGGRAPH_BACKEND_URL}/health`);
    const data = await response.json();
    res.json({
      status: 'connected',
      backend: LANGGRAPH_BACKEND_URL,
      backend_status: data
    });
  } catch (error) {
    res.status(503).json({
      status: 'disconnected',
      backend: LANGGRAPH_BACKEND_URL,
      error: error.message
    });
  }
});

export default router;