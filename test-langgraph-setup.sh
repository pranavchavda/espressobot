#!/bin/bash

echo "🧪 Testing LangGraph setup..."

# Set environment variable for LangGraph mode
export USE_LANGGRAPH=true
export LANGGRAPH_BACKEND_URL=http://localhost:8000

echo "✅ Environment variables set:"
echo "   USE_LANGGRAPH=$USE_LANGGRAPH"
echo "   LANGGRAPH_BACKEND_URL=$LANGGRAPH_BACKEND_URL"

echo "🚀 Now you can start the services:"
echo "   1. Start LangGraph backend: cd langgraph-backend && source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "   2. Start frontend with LangGraph mode: cd frontend && USE_LANGGRAPH=true npm run dev"
echo ""
echo "🔄 The frontend will now:"
echo "   - Proxy chat requests to LangGraph backend (port 8000)"
echo "   - Proxy conversation lists to LangGraph backend"
echo "   - Use PostgreSQL checkpoints for memory persistence"
echo "   - Show only new conversations created with LangGraph"

echo "✨ Previous database conversations will be hidden in LangGraph mode"