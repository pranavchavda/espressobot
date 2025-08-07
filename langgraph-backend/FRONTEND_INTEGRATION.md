# 🔗 Frontend Integration Guide

## Quick Start: Connect Existing Frontend

### Step 1: Start the LangGraph Backend

```bash
cd /home/pranav/espressobot/langgraph-backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 2: Configure Frontend Proxy

The frontend expects the backend at `/api`. Update your frontend proxy configuration:

**Option A: Vite Config** (if using Vite)
```javascript
// frontend/vite.config.js
export default {
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
}
```

**Option B: Package.json Proxy** (if using Create React App)
```json
// frontend/package.json
{
  "proxy": "http://localhost:8000"
}
```

**Option C: Nginx** (Production)
```nginx
location /api {
    proxy_pass http://localhost:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
}
```

### Step 3: Test the Connection

Start your frontend:
```bash
cd /home/pranav/espressobot/frontend
pnpm run dev
```

The frontend should now communicate with the LangGraph backend!

## 🎮 Interactive CLI Testing

We've created a beautiful interactive CLI for testing the backend:

### Basic Usage

```bash
# Interactive mode (recommended)
cd /home/pranav/espressobot/langgraph-backend
source venv/bin/activate
python cli.py

# Single command
python cli.py -m "Find product SKU ESP-001"

# List agents
python cli.py --agents

# Check health
python cli.py --health
```

### CLI Features

- 🎨 **Rich Terminal UI** - Beautiful formatting with colors
- 💬 **Interactive Chat** - Natural conversation flow
- 🤖 **Agent Visibility** - See which agent handles each request
- 📝 **Conversation Export** - Save chats to JSON
- 🔄 **Streaming Support** - Real-time token streaming
- 📊 **Agent List** - View all available agents
- ⚡ **Commands** - Built-in commands for control

### CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help information |
| `/agents` | List available agents |
| `/clear` | Clear conversation history |
| `/export` | Export conversation to JSON |
| `/stream` | Toggle streaming mode |
| `/conv` | Show conversation ID |
| `/new` | Start new conversation |
| `/quit` | Exit the CLI |

### Example Session

```
🤖 EspressoBot LangGraph Backend CLI
Interactive testing interface for the new backend

✓ Connected to backend

┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Agent              ┃ Description                                                    ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ products           │ Handles product searches, SKU lookups, and product queries    │
│ pricing            │ Handles price updates, discounts, and pricing strategies      │
│ inventory          │ Manages inventory levels and stock tracking                   │
└────────────────────┴────────────────────────────────────────────────────────────────┘

Type /help for commands or start chatting!

You: Find me espresso machines under $500

╭─ products ──────────────────────────────────────────────────────────────────╮
│ I found several espresso machines under $500:                               │
│                                                                              │
│ 1. Breville Bambino Plus - $399                                            │
│    SKU: BES500BSS                                                          │
│    Compact design with automatic milk frothing                             │
│                                                                              │
│ 2. De'Longhi Dedica - $299                                                 │
│    SKU: EC685M                                                             │
│    Slim profile, perfect for small kitchens                                │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## API Endpoints Compatibility

The LangGraph backend provides these endpoints that match the frontend expectations:

| Frontend Endpoint | LangGraph Backend | Status |
|------------------|-------------------|---------|
| `/api/agent/run` | `/api/agent/sse` | ✅ Ready |
| `/api/agent/approve` | Not implemented yet | ⚠️ TODO |
| `/api/agent/reject` | Not implemented yet | ⚠️ TODO |
| `/api/agent/interrupt` | Not implemented yet | ⚠️ TODO |
| `/api/conversations` | `/api/conversations` | ✅ Ready |
| `/api/agent-management/agents` | `/api/agent/agents` | ✅ Ready |

## Current Agent Status

### ✅ Migrated Agents
- **Products Agent** - Full production system prompt
- **Pricing Agent** - Basic implementation
- **Inventory Agent** - Basic implementation
- **Sales Agent** - Basic implementation
- **Features Agent** - Basic implementation
- **Media Agent** - Basic implementation
- **Integrations Agent** - Basic implementation
- **Product Management Agent** - Basic implementation
- **Utility Agent** - Basic implementation

### 🔄 Migration Needed
The agents have basic implementations but need:
1. Production system prompts from frontend
2. MCP tool connections
3. Business logic and guardrails

## Next Steps

1. **Test with CLI**: Use the interactive CLI to verify agent behavior
2. **Connect MCP Servers**: Wire up the Python MCP servers for real data
3. **Update Frontend Proxy**: Point frontend to new backend
4. **Test Integration**: Verify frontend-backend communication
5. **Migrate Remaining Logic**: Port approval flows and interrupts

## Troubleshooting

### Backend won't start
```bash
# Check port availability
lsof -i :8000
# Kill existing process if needed
pkill -f uvicorn
```

### Frontend can't connect
```bash
# Check CORS settings in app/main.py
# Verify proxy configuration
# Check network tab in browser DevTools
```

### CLI won't start
```bash
# Ensure backend is running first
# Check virtual environment is activated
# Install dependencies: pip install rich click httpx
```

## Development Workflow

1. **Start Backend**: `uvicorn app.main:app --reload`
2. **Test with CLI**: `python cli.py` (interactive mode)
3. **Monitor Logs**: Backend logs show agent routing
4. **Iterate**: Modify agents, automatic reload applies changes

## Production Deployment

For production, use:
```bash
# With Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker

# With Docker
docker build -t espressobot-langgraph .
docker run -p 8000:8000 espressobot-langgraph
```

---

The LangGraph backend is ready for frontend integration! Use the CLI to test and verify behavior before connecting the production frontend.