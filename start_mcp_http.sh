#!/bin/bash

# Start the MCP HTTP server
echo "Starting MCP HTTP Server on port 8000..."
python -m uvicorn mcp_http_server:app --host 0.0.0.0 --port 8000 --reload
