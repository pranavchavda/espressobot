#!/bin/bash

# Ensure this script is run from the project root directory.
# cd /home/pranav/flask-shopifybot # Or ensure you're there before running

# --- Attempt to source NVM ---
# This allows the script to use nvm to set the correct Node.js version
export NVM_DIR="$HOME/.nvm"
if [ -s "$NVM_DIR/nvm.sh" ]; then
    \. "$NVM_DIR/nvm.sh"
    echo "NVM sourced."
    # Try to use .nvmrc if it exists (project root or frontend)
    if [ -f ".nvmrc" ]; then
        nvm use || echo "Failed to set Node version using root .nvmrc. Continuing with current version."
    elif [ -f "frontend/.nvmrc" ]; then
        (cd frontend && nvm use || echo "Failed to set Node version using frontend/.nvmrc. Continuing with current version.")
    else
        echo "No .nvmrc found. Make sure Node.js v22 (or as required) is active."
        # As per memory: nvm use 22
        nvm use 22 || echo "Failed to set Node.js to v22. Please check your NVM setup and Node installations."
    fi
    node -v # Display current Node version
else
    echo "Warning: NVM script not found. Please ensure NVM is installed and configured correctly if you rely on it."
    echo "Make sure Node.js v22 (or as required by your project) is in your PATH."
fi
# --- End NVM Sourcing ---


PROJECT_DIR=$(pwd)
FLASK_HOST="127.0.0.1"
FLASK_PORT="5000"
# Caddy's listening port is defined in Caddyfile (e.g., 8080)

# --- Prerequisites Check ---
command -v caddy >/dev/null 2>&1 || { echo >&2 "Error: Caddy is not installed. Please install it (see https://caddyserver.com/docs/install). Aborting."; exit 1; }
(cd "${PROJECT_DIR}" && gunicorn --workers 4 --bind "${FLASK_HOST}:${FLASK_PORT}" --log-level debug app:app) &
command -v npm >/dev/null 2>&1 || { echo >&2 "Error: npm is not installed. Please ensure Node.js and npm are set up correctly. Aborting."; exit 1; }

# --- Step 1: Build React Frontend ---
echo ""
echo ">>> Building React frontend..."
(cd "${PROJECT_DIR}/frontend" && npm install && npm run build)
if [ $? -ne 0 ]; then
    echo "Error: React build failed. Exiting."
    exit 1
fi
echo "React frontend built successfully into ${PROJECT_DIR}/frontend/dist."

# --- Step 2: Start Flask Backend with Gunicorn ---
echo ""
echo ">>> Starting Flask backend with Gunicorn on ${FLASK_HOST}:${FLASK_PORT}..."
# Ensure your .env file is in the project root for Flask to pick up environment variables.
# Adjust 'app:app' if your Flask app instance in app.py is named differently,
# or if you use an app factory (e.g., 'app:create_app()').
(cd "${PROJECT_DIR}" && gunicorn --workers 4 --bind "${FLASK_HOST}:${FLASK_PORT}" --log-level debug app:app) &
FLASK_PID=$!
echo "Flask backend started with PID: $FLASK_PID."
# Give Gunicorn a moment to start up
sleep 3
if ! kill -0 $FLASK_PID 2>/dev/null; then
    echo "Error: Flask backend (Gunicorn) failed to start. Exiting."
    exit 1
fi


# --- Step 3: Check for Caddyfile ---
CADDYFILE_PATH="${PROJECT_DIR}/Caddyfile"
if [ ! -f "$CADDYFILE_PATH" ]; then
    echo "Error: Caddyfile not found at ${CADDYFILE_PATH}."
    echo "Please create the Caddyfile as described in the instructions."
    echo "Stopping Flask backend..."
    kill $FLASK_PID
    wait $FLASK_PID 2>/dev/null
    exit 1
fi
echo "Using Caddyfile at ${CADDYFILE_PATH}."

# --- Step 4: Start Caddy ---
echo ""
echo ">>> Starting Caddy..."
# Caddy will automatically find and use the Caddyfile in the current directory.
# 'caddy run' executes Caddy in the foreground and prints logs to stdout/stderr.
(cd "${PROJECT_DIR}" && caddy run) &
CADDY_PID=$!
echo "Caddy started with PID: $CADDY_PID."
sleep 2 # Give Caddy a moment
if ! kill -0 $CADDY_PID 2>/dev/null; then
    echo "Error: Caddy failed to start. Exiting."
    echo "Stopping Flask backend..."
    kill $FLASK_PID
    wait $FLASK_PID 2>/dev/null
    exit 1
fi

# --- Information & Cleanup Handling ---
CADDY_LISTEN_ADDRESS=$(grep -Eo 'http://[^ ]+|https://[^ ]+' "$CADDYFILE_PATH" | head -n 1)
if [ -z "$CADDY_LISTEN_ADDRESS" ]; then
    CADDY_LISTEN_ADDRESS="http://localhost:8080 (Default - check Caddyfile for actual port)"
fi

echo ""
echo "========================================================================"
echo "Application Preview System Status:"
echo " - React Frontend: Built and served from ${PROJECT_DIR}/frontend/dist"
echo " - Flask Backend: Running on ${FLASK_HOST}:${FLASK_PORT} (PID: $FLASK_PID)"
echo " - Caddy Server: Running (PID: $CADDY_PID), proxying to Flask and serving frontend."
echo ""
echo "   Access the application at: ${CADDY_LISTEN_ADDRESS}"
echo "========================================================================"
echo ""
echo "Press Ctrl+C to stop all services."

cleanup() {
    echo ""
    echo ">>> Initiating shutdown..."
    if kill -0 $CADDY_PID 2>/dev/null; then
        echo "Stopping Caddy (PID: $CADDY_PID)..."
        kill $CADDY_PID
        wait $CADDY_PID 2>/dev/null
    else
        echo "Caddy (PID: $CADDY_PID) was not running or already stopped."
    fi

    if kill -0 $FLASK_PID 2>/dev/null; then
        echo "Stopping Flask backend (PID: $FLASK_PID)..."
        kill $FLASK_PID
        wait $FLASK_PID 2>/dev/null
    else
        echo "Flask backend (PID: $FLASK_PID) was not running or already stopped."
    fi

    echo "All services stopped. Exiting."
    exit 0
}

# Trap SIGINT (Ctrl+C) and SIGTERM to call the cleanup function
trap cleanup SIGINT SIGTERM

# Wait for background processes. If any of them exit prematurely,
# the script might continue and exit, or the trap will eventually catch Ctrl+C.
# A more robust solution might involve monitoring both PIDs.
# For now, waiting on Caddy is primary; if it's killed, cleanup runs.
wait $CADDY_PID
# If Caddy exits for any reason, run cleanup
cleanup
