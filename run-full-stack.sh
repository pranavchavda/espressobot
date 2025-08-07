#!/bin/bash

# Script to run both frontend and backend for EspressoBot

echo "🚀 Starting EspressoBot Full Stack..."
echo "=================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup INT

# Start LangGraph Backend
echo -e "${GREEN}Starting LangGraph Backend on port 8000...${NC}"
cd /home/pranav/espressobot/langgraph-backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}Backend failed to start!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Backend running on http://localhost:8000${NC}"

# Start Frontend with LangGraph integration
echo -e "${GREEN}Starting Frontend on port 5173...${NC}"
cd /home/pranav/espressobot/frontend

# Set environment to use LangGraph backend
export USE_LANGGRAPH=true
export LANGGRAPH_BACKEND_URL=http://localhost:8000

# Use pnpm since that's what the frontend uses
pnpm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}✓ Frontend starting on http://localhost:5173${NC}"
echo "=================================="
echo -e "${YELLOW}Services running:${NC}"
echo "  - Frontend: http://localhost:5173"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo "=================================="

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID