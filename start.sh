#!/bin/bash

# ============================================
# EspressoBot Unified Start Script
# Starts both LangGraph backend and Vite frontend
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check if a port is in use
check_port() {
    local port=$1
    # Use ss instead of lsof since lsof might not be available
    if ss -tlnp 2>/dev/null | grep -q ":$port "; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    # Try multiple methods to find and kill the process
    
    # Method 1: Try with ss and extract PID
    local pid=$(ss -tlnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1)
    
    # Method 2: If ss didn't work, try with netstat
    if [ -z "$pid" ]; then
        pid=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | head -1)
    fi
    
    # Method 3: If still no PID, try fuser
    if [ -z "$pid" ]; then
        pid=$(fuser $port/tcp 2>/dev/null | awk '{print $1}')
    fi
    
    if [ ! -z "$pid" ]; then
        print_warning "Killing existing process on port $port (PID: $pid)"
        kill -TERM $pid 2>/dev/null || true
        sleep 1
        # Force kill if still running
        if kill -0 $pid 2>/dev/null; then
            kill -9 $pid 2>/dev/null || true
        fi
    fi
    
    # Last resort: use fuser -k
    if check_port $port; then
        fuser -k $port/tcp 2>/dev/null || true
    fi
}

# Function to wait for service
wait_for_service() {
    local url=$1
    local service=$2
    local max_attempts=30
    local attempt=0
    
    print_info "Waiting for $service to start..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$service is ready!"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
        echo -n "."
    done
    
    echo ""
    print_error "$service failed to start within 30 seconds"
    return 1
}

# Main script
echo "============================================"
echo "       EspressoBot Unified Starter"
echo "============================================"
echo ""

# Check for .env file
if [ ! -f "/home/pranav/ebot/langgraph-backend/.env" ]; then
    print_error ".env file not found at /home/pranav/ebot/langgraph-backend/.env"
    exit 1
fi

print_success "Found .env configuration"

# Check and kill existing processes
print_info "Checking for existing processes..."

# Kill any existing uvicorn processes
pkill -f "uvicorn app.main:app" 2>/dev/null || true

# Kill any existing vite processes
pkill -f "vite" 2>/dev/null || true

if check_port 8000; then
    print_warning "Backend already running on port 8000 - stopping it..."
    kill_port 8000
    sleep 2  # Wait for port to be released
fi

if check_port 5173; then
    print_warning "Frontend already running on port 5173 - stopping it..."
    kill_port 5173
    sleep 2  # Wait for port to be released
fi

# Double-check ports are free
if check_port 8000; then
    print_warning "Port 8000 still in use, force killing..."
    fuser -k 8000/tcp 2>/dev/null || true
    sleep 1
fi

if check_port 5173; then
    print_warning "Port 5173 still in use, force killing..."
    fuser -k 5173/tcp 2>/dev/null || true
    sleep 1
fi

# Final check - if ports still in use, exit with error
if check_port 8000; then
    print_error "Cannot free port 8000. Please manually kill the process using: sudo fuser -k 8000/tcp"
    exit 1
fi

if check_port 5173; then
    print_error "Cannot free port 5173. Please manually kill the process using: sudo fuser -k 5173/tcp"
    exit 1
fi

# Start Backend
echo ""
echo "============================================"
echo "         Starting LangGraph Backend"
echo "============================================"

cd /home/pranav/ebot/langgraph-backend

# Use system python instead of venv since it has all dependencies
print_info "Using system Python (venv has dependency issues)"

# Start backend in background
print_info "Starting backend server on port 8000..."
cd /home/pranav/ebot/langgraph-backend && python run.py > /tmp/espressobot-backend.log 2>&1 &

BACKEND_PID=$!
print_info "Backend PID: $BACKEND_PID"

# Wait for backend to be ready
wait_for_service "http://localhost:8000/health" "Backend"

# Start Frontend
echo ""
echo "============================================"
echo "         Starting Vite Frontend"
echo "============================================"

cd /home/pranav/ebot/frontend

# Check node_modules
if [ ! -d "node_modules" ]; then
    print_warning "node_modules not found. Installing dependencies..."
    npm install
fi

# Start frontend in background
print_info "Starting frontend server on port 5173..."
npm run dev > /tmp/espressobot-frontend.log 2>&1 &

FRONTEND_PID=$!
print_info "Frontend PID: $FRONTEND_PID"

# Wait for frontend to be ready
wait_for_service "http://localhost:5173" "Frontend"

# Success message
echo ""
echo "============================================"
print_success "EspressoBot is running!"
echo "============================================"
echo ""
echo "🚀 Frontend: http://localhost:5173"
echo "🔧 Backend:  http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Logs:"
echo "   Backend:  tail -f /tmp/espressobot-backend.log"
echo "   Frontend: tail -f /tmp/espressobot-frontend.log"
echo ""
echo "🛑 To stop all services: ./stop.sh"
echo ""
echo "💡 Tip: Run './start.sh --logs' to see real-time logs"
echo ""
print_info "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    print_warning "Shutting down services..."
    
    # Kill tail process if running
    if [ ! -z "$TAIL_PID" ] && kill -0 $TAIL_PID 2>/dev/null; then
        kill $TAIL_PID 2>/dev/null || true
    fi
    
    # Kill backend
    if [ ! -z "$BACKEND_PID" ] && kill -0 $BACKEND_PID 2>/dev/null; then
        kill $BACKEND_PID 2>/dev/null || true
        print_info "Backend stopped"
    fi
    
    # Kill frontend
    if [ ! -z "$FRONTEND_PID" ] && kill -0 $FRONTEND_PID 2>/dev/null; then
        kill $FRONTEND_PID 2>/dev/null || true
        print_info "Frontend stopped"
    fi
    
    # Kill any remaining processes on ports
    kill_port 8000
    kill_port 5173
    
    print_success "All services stopped"
    exit 0
}

# Set up trap to cleanup on Ctrl+C
trap cleanup INT TERM

# Option to show logs in real-time
if [ "$1" = "--logs" ] || [ "$1" = "-l" ]; then
    print_info "Showing combined logs (Ctrl+C to stop)..."
    echo ""
    # Use tail with process substitution to show both logs
    tail -f /tmp/espressobot-backend.log /tmp/espressobot-frontend.log 2>/dev/null | while IFS= read -r line; do
        # Color backend logs in blue, frontend in green
        if [[ "$line" == "==> /tmp/espressobot-backend.log <==" ]]; then
            echo -e "\n${BLUE}[BACKEND]${NC}"
        elif [[ "$line" == "==> /tmp/espressobot-frontend.log <==" ]]; then
            echo -e "\n${GREEN}[FRONTEND]${NC}"
        elif [[ "$line" != "==>"* ]]; then
            echo "$line"
        fi
    done &
    TAIL_PID=$!
fi

# Keep script running and monitor processes
while true; do
    # Check if backend is still running
    if [ ! -z "$BACKEND_PID" ] && ! kill -0 $BACKEND_PID 2>/dev/null; then
        print_error "Backend crashed! Check logs: tail -f /tmp/espressobot-backend.log"
        [ ! -z "$TAIL_PID" ] && kill $TAIL_PID 2>/dev/null
        cleanup
    fi
    
    # Check if frontend is still running
    if [ ! -z "$FRONTEND_PID" ] && ! kill -0 $FRONTEND_PID 2>/dev/null; then
        print_error "Frontend crashed! Check logs: tail -f /tmp/espressobot-frontend.log"
        [ ! -z "$TAIL_PID" ] && kill $TAIL_PID 2>/dev/null
        cleanup
    fi
    
    sleep 5
done