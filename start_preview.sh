# #!/bin/bash

# # Start Python backend in the background
# echo "Starting Python backend..."
# python3 app.py &
# PYTHON_PID=$!
# echo "Python backend started with PID: $PYTHON_PID"

# # Navigate to the frontend directory
# cd frontend/

# # Source NVM and set Node version
# echo "Setting up Node.js environment..."
# # Assuming nvm is installed in the default location
# if [ -s "$HOME/.nvm/nvm.sh" ]; then
#   source "$HOME/.nvm/nvm.sh"  # This loads nvm
#   nvm use 22
# elif command -v brew >/dev/null 2>&1 && [ -s "$(brew --prefix nvm)/nvm.sh" ]; then # Check for Homebrew nvm on macOS
#     source "$(brew --prefix nvm)/nvm.sh"
#     nvm use 22
# else
#     echo "NVM script not found. Please ensure NVM is installed and configured correctly."
#     echo "Attempting to run 'npm run dev' directly..."
# fi

# # Build frontend before starting preview
# echo "Building frontend..."
# npm run build

# # Start frontend preview server on port 5173
# echo "Starting frontend preview server on port 5173..."
# npm run preview --port=5173

# # Function to clean up background process on exit
# cleanup() {
#     echo "Stopping Python backend (PID: $PYTHON_PID)..."
#     kill $PYTHON_PID
#     exit
# }

# # Trap EXIT signal to run cleanup function
# trap cleanup EXIT SIGINT SIGTERM

# # Keep the script running without exiting
# while true; do
#   sleep 60
# done
#!/bin/bash

# Set up Python environment
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
uvicorn app:app --host 127.0.0.1 --port 5000 --reload &
PYTHON_PID=$!
echo "Python Uvicorn backend started with PID: $PYTHON_PID"

# Wait for the backend to fully initialize
echo "Waiting for backend to initialize..."
sleep 5

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

# Install frontend dependencies
echo "Installing frontend dependencies..."
npm install

# Build the frontend
echo "Building frontend..."
npm run build

# Start frontend preview server on port 5173
echo "Starting frontend preview server on port 5173..."
npx vite preview --port 5173 --host 0.0.0.0 &

# Function to clean up background process on exit
cleanup() {
    echo "Stopping Python Uvicorn backend (PID: $PYTHON_PID)..."
    kill $PYTHON_PID
    exit
}

# Trap EXIT signal to run cleanup function
trap cleanup EXIT SIGINT SIGTERM

# Wait for frontend preview process to finish
wait $!
