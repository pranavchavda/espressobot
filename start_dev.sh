#!/bin/bash

# Start Python backend in the background
echo "Starting Python backend..."
python3 app.py &
PYTHON_PID=$!
echo "Python backend started with PID: $PYTHON_PID"
# Wait for the backend to fully initialize
echo "Waiting for backend to initialize..."
sleep 5  # Increased wait time

# Check if the server is running
if ! curl -s http://0.0.0.0:5000 > /dev/null; then
  echo "Warning: Backend server may not be running correctly. Continuing anyway..."
fi

# Navigate to the frontend directory
cd frontend/

# For Replit environment, don't rely on NVM
echo "Setting up Node.js environment for Replit..."
export NODE_ENV=development

# Start frontend development server
echo "Starting frontend development server..."
npm run dev -- --port=2000 --host=0.0.0.0

# Function to clean up background process on exit
cleanup() {
    echo "Stopping Python backend (PID: $PYTHON_PID)..."
    kill $PYTHON_PID
    exit
}

# Trap EXIT signal to run cleanup function
trap cleanup EXIT SIGINT SIGTERM

# Wait for npm run dev to finish
wait $!
