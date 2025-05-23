#!/bin/bash

# Activate virtual environment (if your venv is named 'myenv')
if [ -f "myenv/bin/activate" ]; then
    echo "Activating Python virtual environment..."
    source myenv/bin/activate
else
    echo "Warning: Virtual environment 'myenv' not found. Assuming Python dependencies are globally available or venv is already active."
fi

# Start Python backend with Uvicorn in the background
echo "Starting Python backend with Uvicorn..."
# Using 127.0.0.1 for host, as Caddy is the entry point
uvicorn app:application --host 0.0.0.0 --port 5000 --reload &
PYTHON_PID=$!
echo "Python Uvicorn backend started with PID: $PYTHON_PID"
# Wait for the backend to fully initialize
echo "Waiting for backend to initialize..."
sleep 15  # Increased wait time

# Check if the server is running (using 127.0.0.1 as Uvicorn is now bound to it)
if ! curl -s http://127.0.0.1:5000 > /dev/null; then
  echo "Warning: Backend server may not be running correctly. Continuing anyway..."
fi

# Navigate to the frontend directory
cd frontend/

# For Replit environment, don't rely on NVM
echo "Setting up Node.js environment for Replit..."
export NODE_ENV=development

export TOKENIZERS_PARALLELISM=false 

# Start frontend development server
echo "Starting frontend development server..."
npm run dev -- --port=2000 --host=0.0.0.0

# Function to clean up background process on exit
cleanup() {
    echo "Stopping Python Uvicorn backend (PID: $PYTHON_PID)..."
    kill $PYTHON_PID
    exit
}

# Trap EXIT signal to run cleanup function
trap cleanup EXIT SIGINT SIGTERM

# Wait for npm run dev to finish
wait $!
