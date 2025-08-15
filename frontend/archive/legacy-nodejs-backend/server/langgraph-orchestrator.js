/**
 * LangGraph Backend Orchestrator
 * Routes requests to the new LangGraph backend instead of the bash orchestrator
 */

import express from 'express';

const router = express.Router();

// LangGraph backend URL
const LANGGRAPH_BACKEND = process.env.LANGGRAPH_BACKEND_URL || 'http://localhost:8000';

console.log(`🔗 LangGraph Orchestrator: Routing to backend at ${LANGGRAPH_BACKEND}`);

// Non-streaming endpoint - simpler and more reliable
router.post('/message', async (req, res) => {
  try {
    console.log('[LangGraph Proxy] Non-streaming request to backend...');
    
    // Add user_id from authenticated user to the request body
    const requestBody = {
      ...req.body,
      user_id: req.user?.id?.toString() || "1"
    };
    
    // Forward to the non-streaming endpoint
    const response = await fetch(`${LANGGRAPH_BACKEND}/api/agent/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    const result = await response.json();
    
    // Return the result directly
    res.json(result);
  } catch (error) {
    console.error('[LangGraph Proxy] Error:', error);
    res.status(500).json({ error: error.message });
  }
});

// Main chat endpoint - proxy to LangGraph backend with NDJSON to SSE conversion
router.post('/run', async (req, res) => {
  try {
    console.log('[LangGraph Proxy] Forwarding request to backend...');
    
    // Add user_id from authenticated user to the request body
    const requestBody = {
      ...req.body,
      user_id: req.user?.id?.toString() || "1"  // Convert to string and default to "1"
    };
    
    console.log('[LangGraph Proxy] User ID:', requestBody.user_id);
    
    // Forward the request to LangGraph backend without timeout for long-running tasks
    const response = await fetch(`${LANGGRAPH_BACKEND}/api/agent/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody),
    });

    // Set SSE headers for frontend compatibility
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');

    // Convert NDJSON stream to SSE format using standard streams API
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          // Process any remaining data in buffer
          if (buffer.trim()) {
            try {
              const data = JSON.parse(buffer);
              if (data.event === 'done') {
                res.write(`event: done\n`);
                res.write(`data: ${JSON.stringify({ message: data.message })}\n\n`);
              }
            } catch (e) {
              console.error('[LangGraph Proxy] Error parsing final buffer:', e);
            }
          }
          break;
        }
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer
        
        for (const line of lines) {
          if (line.trim()) {
            try {
              const data = JSON.parse(line);
              
              // Convert to SSE format expected by frontend
              if (data.event === 'conversation_id') {
                // Forward conversation_id event
                res.write(`event: conversation_id\n`);
                res.write(`data: ${JSON.stringify({
                  conv_id: data.conv_id,
                  thread_id: data.thread_id
                })}\n\n`);
              } else if (data.event === 'agent_message') {
                res.write(`event: agent_message\n`);
                res.write(`data: ${JSON.stringify({
                  agent: data.agent,
                  content: data.message,  // Frontend expects 'content' not 'message'
                  tokens: data.tokens
                })}\n\n`);
              } else if (data.event === 'agent_complete') {
                res.write(`event: agent_complete\n`);
                res.write(`data: ${JSON.stringify({
                  agent: data.agent,
                  message: data.message
                })}\n\n`);
              } else if (data.event === 'done') {
                res.write(`event: done\n`);
                res.write(`data: ${JSON.stringify({
                  message: data.message
                })}\n\n`);
                // Close the stream when done is received
                res.end();
                return;
              } else if (data.event === 'error') {
                res.write(`event: error\n`);
                res.write(`data: ${JSON.stringify({
                  error: data.error
                })}\n\n`);
              }
            } catch (e) {
              console.error('[LangGraph Proxy] Error parsing JSON:', e, 'Line:', line);
            }
          }
        }
      }
    } catch (error) {
      console.error('[LangGraph Proxy] Stream error:', error);
      res.write(`event: error\n`);
      res.write(`data: ${JSON.stringify({ error: error.message })}\n\n`);
    } finally {
      res.end();
    }
    
  } catch (error) {
    console.error('[LangGraph Proxy] Error:', error);
    res.status(500).json({
      error: 'Failed to connect to LangGraph backend',
      details: error.message
    });
  }
});

// Message endpoint (non-streaming)
router.post('/message', async (req, res) => {
  try {
    const response = await fetch(`${LANGGRAPH_BACKEND}/api/agent/message`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });

    const data = await response.json();
    res.json(data);
  } catch (error) {
    console.error('[LangGraph Proxy] Error:', error);
    res.status(500).json({
      error: 'Failed to connect to LangGraph backend',
      details: error.message
    });
  }
});

// Health check
router.get('/health', async (req, res) => {
  try {
    const response = await fetch(`${LANGGRAPH_BACKEND}/health`);
    const data = await response.json();
    res.json({
      frontend: 'healthy',
      backend: data,
      backend_url: LANGGRAPH_BACKEND
    });
  } catch (error) {
    res.status(503).json({
      frontend: 'healthy',
      backend: 'unreachable',
      backend_url: LANGGRAPH_BACKEND,
      error: error.message
    });
  }
});

// List available agents
router.get('/agents', async (req, res) => {
  res.json({
    agents: [
      'products',
      'pricing', 
      'inventory',
      'sales',
      'features',
      'media',
      'integrations',
      'product_management',
      'utility',
      'graphql',
      'orders'
    ],
    backend: 'LangGraph with Native MCP'
  });
});

export default router;