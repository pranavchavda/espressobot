#!/bin/bash

# ============================================
# EspressoBot Stop Script
# Stops both backend and frontend services
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
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to kill process on port
kill_port() {
    local port=$1
    local service=$2
    local pids=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null)
    
    if [ ! -z "$pids" ]; then
        print_info "Stopping $service on port $port (PID: $pids)"
        kill -TERM $pids 2>/dev/null || true
        sleep 1
        
        # Force kill if still running
        if kill -0 $pids 2>/dev/null; then
            print_warning "Force killing $service"
            kill -9 $pids 2>/dev/null || true
        fi
        print_success "$service stopped"
    else
        print_info "$service not running on port $port"
    fi
}

# Main script
echo "============================================"
echo "       EspressoBot Stop Script"
echo "============================================"
echo ""

# Stop frontend
print_info "Stopping frontend..."
kill_port 5173 "Frontend"

# Kill any vite processes
pkill -f "vite" 2>/dev/null || true

# Stop backend
print_info "Stopping backend..."
kill_port 8000 "Backend"

# Kill any uvicorn processes
pkill -f "uvicorn app.main:app" 2>/dev/null || true

# Clean up any stray node processes related to EspressoBot
print_info "Cleaning up stray processes..."
pkill -f "espressobot" 2>/dev/null || true

echo ""
print_success "All EspressoBot services stopped"
echo ""
echo "To restart: ./start.sh"