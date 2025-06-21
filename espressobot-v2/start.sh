#.!/bin/bash

# EspressoBot v0.2 Startup Script
# This script starts both the backend and frontend servers

echo "🚀 Starting EspressoBot v0.2..."

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down EspressoBot...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit
}

# Set up trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Check prerequisites
echo "Checking prerequisites..."

if ! command_exists python3 && ! command_exists python; then
    echo -e "${RED}❌ Python is not installed${NC}"
    exit 1
fi

if ! command_exists node; then
    echo -e "${RED}❌ Node.js is not installed${NC}"
    exit 1
fi

if ! command_exists pnpm; then
    echo -e "${RED}❌ pnpm is not installed${NC}"
    echo "Install with: npm install -g pnpm"
    exit 1
fi

# Backend setup
echo -e "\n${GREEN}Setting up backend...${NC}"
cd "$SCRIPT_DIR/python-backend"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv || python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade pip
pip install --upgrade pip >/dev/null 2>&1

# Install requirements if needed
if [ ! -f ".deps_installed" ] || [ "requirements.txt" -nt ".deps_installed" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    touch .deps_installed
else
    echo "Python dependencies already installed"
fi

# Check for OpenAI API key
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating one...${NC}"
    echo "# OpenAI API Configuration" > .env
    
    # Check if OPENAI_API_KEY exists in environment
    if [ ! -z "$OPENAI_API_KEY" ]; then
        echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env
        echo -e "${GREEN}✅ Using OpenAI API key from environment${NC}"
    else
        echo "OPENAI_API_KEY=your-api-key-here" >> .env
        echo -e "${RED}❌ Please set OPENAI_API_KEY environment variable or add it to python-backend/.env${NC}"
        exit 1
    fi
fi

# Check if API key is set in .env
if grep -q "your-api-key-here" .env; then
    # Try to use environment variable if available
    if [ ! -z "$OPENAI_API_KEY" ]; then
        echo -e "${YELLOW}Updating .env with OpenAI API key from environment...${NC}"
        sed -i "s/your-api-key-here/$OPENAI_API_KEY/" .env
    else
        echo -e "${RED}❌ Please set OPENAI_API_KEY environment variable or update python-backend/.env${NC}"
        exit 1
    fi
fi

# Start backend server
echo -e "${GREEN}Starting backend server on http://localhost:8000${NC}"
python run.py &
BACKEND_PID=$!

# Wait for backend to start
echo "Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/docs >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is running${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Backend failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Frontend setup
echo -e "\n${GREEN}Setting up frontend...${NC}"
cd "$SCRIPT_DIR/ui"

# Install pnpm dependencies if needed
if [ ! -d "node_modules" ] || [ "package.json" -nt "node_modules" ]; then
    echo "Installing pnpm dependencies..."
    pnpm install
else
    echo "pnpm dependencies already installed"
fi

# Start frontend server
echo -e "${GREEN}Starting frontend server on http://localhost:3000${NC}"
pnpm dev &
FRONTEND_PID=$!

# Wait for frontend to start
echo "Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:3000 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is running${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Frontend failed to start${NC}"
        exit 1
    fi
    sleep 1
done

# Success message
echo -e "\n${GREEN}🎉 EspressoBot v0.2 is running!${NC}"
echo -e "${GREEN}📡 Backend API: http://localhost:8000${NC}"
echo -e "${GREEN}💻 Frontend UI: http://localhost:3000${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Keep script running and show logs
wait
