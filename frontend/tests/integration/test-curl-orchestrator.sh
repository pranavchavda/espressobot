#!/bin/bash

echo "Testing orchestrator API with MCP tool request..."

# Use the correct port (5174 based on the log)
curl -X POST http://localhost:5174/api/agent/run \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "message": "Get product details for CF-MEX-ALT", 
    "conv_id": "test-mcp-direct"
  }' \
  -N 2>&1 | head -100