#!/bin/bash

# Start Python backend in the background
echo "Starting Python backend..."
python3 app.py &
PYTHON_PID=$!
echo "Python backend started with PID: $PYTHON_PID"

# Navigate to the frontend directory
cd frontend/

# Source NVM and set Node version
echo "Setting up Node.js environment..."
# Assuming nvm is installed in the default location
if [ -s "$HOME/.nvm/nvm.sh" ]; then
  source "$HOME/.nvm/nvm.sh"  # This loads nvm
  nvm use 22
elif [ -s "$(brew --prefix nvm)/nvm.sh" ]; then # Check for Homebrew nvm on macOS
    source "$(brew --prefix nvm)/nvm.sh"
    nvm use 22
else
    echo "NVM script not found. Please ensure NVM is installed and configured correctly."
    echo "Attempting to run 'npm run dev' directly..."
fi

# Build frontend before starting preview
echo "Building frontend..."
npm run build

# Start frontend preview server on port 2000
echo "Starting frontend preview server on port 2000..."
npm run preview --port=2000

# Function to clean up background process on exit
cleanup() {
    echo "Stopping Python backend (PID: $PYTHON_PID)..."
    kill $PYTHON_PID
    exit
}

# Trap EXIT signal to run cleanup function
trap cleanup EXIT SIGINT SIGTERM

# Wait for npm run dev to finish (which typically runs until manually stopped)
# This 'wait' will keep the script alive. If npm dev exits, the script exits, triggering the trap.
wait $!
