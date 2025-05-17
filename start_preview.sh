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
if [ -d "venv" ]; then
  source venv/bin/activate
else
  echo "[WARNING] No venv found! Running with system Python. It is recommended to use a virtual environment in ./venv."
fi

# Start the Python backend in the background
echo "Starting Python backend..."
python app.py &
PYTHON_PID=$!
echo "Python backend started with PID: $PYTHON_PID"

# Navigate to frontend directory
cd frontend

# Build the frontend
echo "Building frontend..."
npm install
npm run build

# Start the frontend on port 5173 to match the port forwarding in .replit
echo "Starting frontend on port 5173..."
npx vite preview --port 5173 --host 0.0.0.0
