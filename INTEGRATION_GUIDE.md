# 🚀 EspressoBot Integration Guide

## Frontend + LangGraph Backend Integration

### Quick Start

#### Method 1: Run Both Together (Recommended)
```bash
# Run the full stack script
./run-full-stack.sh
```

This will:
- Start LangGraph backend on port 8000
- Start React frontend on port 5173
- Frontend will use the LangGraph backend for all agent operations

#### Method 2: Run Separately

**Terminal 1 - Backend:**
```bash
cd langgraph-backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
# Use the LangGraph backend
export USE_LANGGRAPH=true
export LANGGRAPH_BACKEND_URL=http://localhost:8000
pnpm run dev
```

### Testing the Integration

1. **Test Backend Only:**
```bash
cd langgraph-backend
source .venv/bin/activate
python test_backend.py
```

2. **Test via CLI:**
```bash
cd langgraph-backend
python cli.py
>>> Find product with SKU IDC-MBC-T-S
>>> What's the price of Breville Barista Express?
```

3. **Test via Frontend:**
- Open http://localhost:5173
- Send messages like:
  - "Find all Breville products"
  - "Update price of SKU ABC-123 to $49.99"
  - "Show me today's sales"

### Architecture

```
┌─────────────────┐         ┌──────────────────┐
│  React Frontend │ ──SSE──> │ LangGraph Backend│
│   (Port 5173)   │         │   (Port 8000)    │
└─────────────────┘         └──────────────────┘
                                     │
                            ┌────────▼────────┐
                            │  Native MCP     │
                            │    Agents       │
                            └────────┬────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             ┌──────────┐     ┌──────────┐    ┌──────────┐
             │ Products │     │ Pricing  │    │  Sales   │
             │   MCP    │     │   MCP    │    │   MCP    │
             └──────────┘     └──────────┘    └──────────┘
```

### Available Agents

All agents are now using native MCP pattern with automatic tool discovery:

1. **Products Agent** - Product search, creation, management
2. **Pricing Agent** - Price updates, MAP compliance
3. **Inventory Agent** - Stock management, policies
4. **Sales Agent** - MAP sales, analytics
5. **Features Agent** - Metafields, specifications
6. **Media Agent** - Image management
7. **Integrations Agent** - SkuVault, Yotpo
8. **Product Management Agent** - Advanced operations
9. **Utility Agent** - Memory, research
10. **GraphQL Agent** - Custom API queries
11. **Orders Agent** - Order analytics

### Configuration

**Backend Environment (.env):**
```env
ANTHROPIC_API_KEY=your-key
SHOPIFY_SHOP_URL=your-shop.myshopify.com
SHOPIFY_ACCESS_TOKEN=your-token
DATABASE_URL=sqlite+aiosqlite:///./espressobot.db
LOG_LEVEL=INFO
```

**Frontend Environment (.env):**
```env
# Use LangGraph backend
USE_LANGGRAPH=true
LANGGRAPH_BACKEND_URL=http://localhost:8000

# Your API keys (for frontend features)
OPENAI_API_KEY=your-key
# ... other keys
```

### Troubleshooting

**Backend won't start:**
```bash
# Reinstall dependencies
cd langgraph-backend
source .venv/bin/activate
pip install -r requirements.txt
```

**Frontend can't connect:**
- Check CORS settings in `langgraph-backend/app/main.py`
- Ensure backend is running on port 8000
- Check browser console for errors

**MCP tools not loading:**
- Check MCP server paths in agent files
- Ensure Python tools are accessible
- Check `PYTHONPATH` in MCP server configs

### Development Workflow

1. **Adding new tools:** Add to appropriate MCP server in `frontend/python-tools/`
2. **Creating new agents:** Follow pattern in `langgraph-backend/app/agents/`
3. **Testing changes:** Use CLI first, then test in frontend
4. **Debugging:** Check logs in both frontend console and backend terminal

### Next Steps

- [ ] Add conversation persistence
- [ ] Implement authentication
- [ ] Add Google Workspace integration
- [ ] Set up monitoring/observability
- [ ] Deploy to production

---

**Status:** ✅ All core agents migrated to native MCP pattern and integrated with frontend!