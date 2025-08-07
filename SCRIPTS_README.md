# EspressoBot Management Scripts

## Overview
Three shell scripts to manage the EspressoBot application (backend + frontend).

## Scripts

### 🚀 `start.sh`
Starts both the LangGraph backend and Vite frontend.

**Features:**
- Checks for existing processes and prompts to kill them
- Activates Python virtual environment for backend
- Starts services in background with logging
- Monitors services and restarts if they crash
- Graceful shutdown on Ctrl+C

**Usage:**
```bash
./start.sh
```

### 🛑 `stop.sh`
Stops all EspressoBot services.

**Features:**
- Gracefully stops both backend and frontend
- Cleans up stray processes
- Force kills if services don't stop gracefully

**Usage:**
```bash
./stop.sh
```

### 📊 `status.sh`
Shows the current status of all services.

**Features:**
- Shows which services are running/stopped
- Displays service health status
- Shows available URLs
- Displays last error from log files
- Quick action reminders

**Usage:**
```bash
./status.sh
```

## Service Details

### Backend (LangGraph)
- **Port:** 8000
- **URL:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Log:** `/tmp/espressobot-backend.log`
- **Technology:** FastAPI + LangGraph + 14 specialized agents

### Frontend (Vite)
- **Port:** 5173
- **URL:** http://localhost:5173
- **Log:** `/tmp/espressobot-frontend.log`
- **Technology:** React + Vite + Tailwind CSS

## Common Operations

### Start Everything
```bash
./start.sh
```

### Stop Everything
```bash
./stop.sh
```

### Check Status
```bash
./status.sh
```

### Restart Everything
```bash
./stop.sh && ./start.sh
```

### View Backend Logs
```bash
tail -f /tmp/espressobot-backend.log
```

### View Frontend Logs
```bash
tail -f /tmp/espressobot-frontend.log
```

## Troubleshooting

### Port Already in Use
If you see "Address already in use" errors:
1. Run `./stop.sh` to clean up
2. If that doesn't work: `lsof -i :8000` or `lsof -i :5173` to find the process
3. Kill the process: `kill -9 <PID>`

### Backend Crashes
Check the logs:
```bash
tail -100 /tmp/espressobot-backend.log
```

### Frontend Won't Start
Check if node_modules exists:
```bash
cd frontend && npm install
```

### OAuth Errors
Ensure Google OAuth credentials are configured in `.env`:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`

## Environment Variables
All configuration is in `/home/pranav/espressobot/.env`

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - For Claude AI
- `OPENAI_API_KEY` - For OpenAI fallback
- `GOOGLE_CLIENT_ID/SECRET` - For OAuth
- `SHOPIFY_*` - Shopify API credentials

## Architecture
- **14 Specialized Agents**: Products, Pricing, Inventory, Sales, Features, Media, Integrations, Product Management, Utility, GraphQL, Orders, Google Workspace, GA4 Analytics, General
- **Unified Database**: PostgreSQL on node.idrinkcoffee.info
- **Memory System**: PostgreSQL with pgvector for embeddings
- **MCP Servers**: Model Context Protocol for tool integration