#!/bin/bash

# ============================================
# EspressoBot Status Check Script
# Shows status of all services
# ============================================

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
    echo -e "${GREEN}[RUNNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[STOPPED]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to check service status
check_service() {
    local port=$1
    local service=$2
    local url=$3
    
    # Check if port is in use
    local pids=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null)
    
    if [ ! -z "$pids" ]; then
        # Check if service is responding
        if curl -s "$url" > /dev/null 2>&1; then
            print_success "$service on port $port (PID: $pids) - Healthy"
        else
            print_warning "$service on port $port (PID: $pids) - Not responding"
        fi
    else
        print_error "$service on port $port - Not running"
    fi
}

# Main script
echo "============================================"
echo "       EspressoBot Status Check"
echo "============================================"
echo ""

# Check backend
check_service 8000 "Backend" "http://localhost:8000/health"

# Check frontend
check_service 5173 "Frontend" "http://localhost:5173"

echo ""
echo "============================================"
echo "       Service URLs"
echo "============================================"
echo ""

# Check if backend is accessible
if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then
    echo "🔧 Backend:  http://localhost:8000"
    echo "📊 API Docs: http://localhost:8000/docs"
else
    echo "❌ Backend:  Not accessible"
fi

# Check if frontend is accessible
if curl -s "http://localhost:5173" > /dev/null 2>&1; then
    echo "🚀 Frontend: http://localhost:5173"
else
    echo "❌ Frontend: Not accessible"
fi

echo ""
echo "============================================"
echo "       Log Files"
echo "============================================"
echo ""

# Check log files
if [ -f "/tmp/espressobot-backend.log" ]; then
    echo "📝 Backend log:  tail -f /tmp/espressobot-backend.log"
    echo "   Last error: $(grep -i error /tmp/espressobot-backend.log | tail -1 | cut -c1-60)..."
else
    echo "📝 Backend log:  Not found"
fi

if [ -f "/tmp/espressobot-frontend.log" ]; then
    echo "📝 Frontend log: tail -f /tmp/espressobot-frontend.log"
    echo "   Last error: $(grep -i error /tmp/espressobot-frontend.log | tail -1 | cut -c1-60)..."
else
    echo "📝 Frontend log: Not found"
fi

echo ""
echo "============================================"
echo "       Quick Actions"
echo "============================================"
echo ""
echo "▶️  Start all:  ./start.sh"
echo "⏹️  Stop all:   ./stop.sh"
echo "🔄 Restart:    ./stop.sh && ./start.sh"
echo ""