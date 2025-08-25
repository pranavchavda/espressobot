# LangGraph Backend Database Setup

This guide explains how to set up a separate database for the langgraph-backend system.

## Overview

The langgraph-backend system now has its own dedicated database configuration to avoid conflicts with the existing system. The new database is named `espressobot_langgraph`.

## Quick Setup

### Option 1: Automated Setup (Recommended)

1. **Run the setup script:**
   ```bash
   cd /home/pranav/ebot/langgraph-backend
   python setup_langgraph_database.py
   ```

2. **Use the new configuration:**
   ```bash
   cp .env.langgraph .env
   ```

3. **Start the server:**
   ```bash
   python run.py
   ```

### Option 2: Manual Setup

If the automated script fails due to permissions, follow these steps:

1. **Create the database manually:**
   ```bash
   sudo -u postgres psql -c "CREATE DATABASE espressobot_langgraph OWNER espressobot;"
   ```

2. **Apply the schema:**
   ```bash
   PGPASSWORD=localdev123 psql -h localhost -U espressobot -d espressobot_langgraph -f schema.sql
   ```

3. **Use the new configuration:**
   ```bash
   cp .env.langgraph .env
   ```

## Database Configuration

### New Database Details
- **Database Name:** `espressobot_langgraph`
- **URL:** `postgresql://espressobot:localdev123@localhost:5432/espressobot_langgraph`
- **Port:** Server runs on port 8001 (instead of 8000)
- **User:** Same (`espressobot`)
- **Password:** Same (`localdev123`)

### Configuration Files

- **`.env.langgraph`** - New environment configuration
- **`setup_langgraph_database.py`** - Automated setup script
- **`schema.sql`** - Database schema (unchanged)

## What's Included

### Schema Tables
- `memories` - Memory system with pgvector embeddings
- `prompt_fragments` - Agent-specific context
- `memory_duplicates` - Deduplication tracking
- `memory_analytics` - Usage analytics
- Plus all required indexes and triggers

### Data Migration
The setup script copies only essential configuration data:
- Agent configurations
- System prompt fragments
- **Excludes:** User conversations, memories, analytics

## Verification

After setup, verify the database is working:

```bash
# Check database exists
PGPASSWORD=localdev123 psql -h localhost -U espressobot -l | grep langgraph

# Check tables
PGPASSWORD=localdev123 psql -h localhost -U espressobot -d espressobot_langgraph -c "\\dt"

# Check pgvector extension
PGPASSWORD=localdev123 psql -h localhost -U espressobot -d espressobot_langgraph -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

## Server Configuration

The new configuration includes optimized settings:

### Model Configuration
- **Orchestrator:** GPT-5
- **Primary:** GPT-5-mini  
- **Auxiliary:** GPT-5-nano
- **Specialized:** DeepSeek Chat

### Orchestrator Settings
- **Max Context:** 10,000 tokens
- **Compression Threshold:** 60,000 tokens
- **Max Agent Calls:** 7
- **Agent Timeout:** 90 seconds

### Server Settings
- **Port:** 8001 (different from original 8000)
- **Environment:** Development
- **Logging:** INFO level with structured logging
- **Tracing:** Enabled for all operations

## Troubleshooting

### Database Creation Fails
If you get "permission denied to create database":
```bash
sudo -u postgres psql -c "CREATE DATABASE espressobot_langgraph OWNER espressobot;"
```

### Connection Issues
Verify PostgreSQL is running and accessible:
```bash
PGPASSWORD=localdev123 psql -h localhost -U espressobot -d postgres -c "SELECT version();"
```

### Schema Issues
If tables are missing, reapply the schema:
```bash
PGPASSWORD=localdev123 psql -h localhost -U espressobot -d espressobot_langgraph -f schema.sql
```

### Port Conflicts
If port 8001 is in use, update PORT in `.env`:
```bash
PORT=8002
```

## File Structure

```
langgraph-backend/
├── .env.langgraph              # New configuration file
├── setup_langgraph_database.py # Automated setup script
├── LANGGRAPH_DATABASE_SETUP.md # This documentation
├── schema.sql                  # Database schema
└── run.py                      # Server startup
```

## Next Steps

After successful setup:

1. **Start the server:** `python run.py`
2. **Access the API:** `http://localhost:8001/api/agent`
3. **Check logs:** Monitor console output for any issues
4. **Test agents:** Send test requests to verify functionality

The system is now ready with its own dedicated database instance.