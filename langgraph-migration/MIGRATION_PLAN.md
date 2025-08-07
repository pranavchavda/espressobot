# Detailed Migration Plan

## Phase 1: Parallel Development (Week 1-2)

### Project Setup

#### Directory Structure
```
/home/pranav/espressobot/langgraph-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── orchestrator.py          # Main LangGraph orchestrator
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py             # Base agent class
│   │   ├── products.py         # Products specialist
│   │   ├── pricing.py          # Pricing specialist
│   │   ├── inventory.py        # Inventory management
│   │   ├── sales.py            # Sales campaigns
│   │   ├── features.py         # Features/metafields
│   │   ├── media.py            # Media management
│   │   ├── integrations.py     # External integrations
│   │   ├── product_mgmt.py     # Product creation/management
│   │   ├── utility.py          # Memory/utility operations
│   │   ├── documentation.py    # API documentation
│   │   ├── orders.py           # Order management
│   │   ├── google_workspace.py # Google integrations
│   │   ├── analytics.py        # GA4 analytics
│   │   └── swe.py              # Code assistance
│   ├── state/
│   │   ├── __init__.py
│   │   ├── graph_state.py      # State definitions
│   │   ├── checkpoints.py      # Persistence layer
│   │   └── memory.py           # Memory management
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── mcp_client.py       # MCP server connections
│   │   ├── bash.py             # Bash execution
│   │   └── file_ops.py         # File operations
│   ├── api/
│   │   ├── __init__.py
│   │   ├── chat.py             # SSE chat endpoint
│   │   ├── conversations.py    # Conversation management
│   │   ├── auth.py             # Authentication
│   │   ├── memory.py           # Memory endpoints
│   │   └── dashboard.py        # Dashboard analytics
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── session.py          # Database sessions
│   │   └── migrations/         # Alembic migrations
│   └── utils/
│       ├── __init__.py
│       ├── streaming.py        # SSE utilities
│       └── logger.py           # Logging configuration
├── tests/
│   ├── test_agents.py
│   ├── test_orchestrator.py
│   ├── test_mcp.py
│   └── test_api.py
├── requirements.txt
├── .env.example
└── docker-compose.yml           # Local development setup
```

### Core Components Implementation

#### 1. FastAPI Backend Setup
```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import chat, conversations, auth

app = FastAPI(title="EspressoBot LangGraph Backend")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(chat.router, prefix="/api/agent")
app.include_router(conversations.router, prefix="/api/conversations")
app.include_router(auth.router, prefix="/api/auth")
```

#### 2. LangGraph Orchestrator
```python
# orchestrator.py
from langgraph.graph import StateGraph, END
from app.agents import products, pricing, inventory

class Orchestrator:
    def __init__(self):
        self.graph = self._build_graph()
    
    def _build_graph(self):
        graph = StateGraph()
        
        # Add agent nodes
        graph.add_node("router", self.route_request)
        graph.add_node("products", products.ProductsAgent())
        graph.add_node("pricing", pricing.PricingAgent())
        
        # Define edges
        graph.add_conditional_edges("router", self.determine_agent)
        
        return graph.compile()
```

#### 3. MCP Integration
```python
# tools/mcp_client.py
from langchain_community.tools import MCPClient
import os

class MCPManager:
    def __init__(self):
        self.servers = self._initialize_servers()
    
    def _initialize_servers(self):
        base_path = "/home/pranav/espressobot/frontend/python-tools"
        return {
            "products": MCPClient(f"stdio://{base_path}/mcp-products-server.py"),
            "pricing": MCPClient(f"stdio://{base_path}/mcp-pricing-server.py"),
            "inventory": MCPClient(f"stdio://{base_path}/mcp-inventory-server.py"),
            "sales": MCPClient(f"stdio://{base_path}/mcp-sales-server.py"),
            "features": MCPClient(f"stdio://{base_path}/mcp-features-server.py"),
            "media": MCPClient(f"stdio://{base_path}/mcp-media-server.py"),
            "integrations": MCPClient(f"stdio://{base_path}/mcp-integrations-server.py"),
            "product_mgmt": MCPClient(f"stdio://{base_path}/mcp-product-management-server.py"),
            "utility": MCPClient(f"stdio://{base_path}/mcp-utility-server.py"),
            "graphql": MCPClient(f"stdio://{base_path}/mcp-graphql-server.py"),
            "orders": MCPClient(f"stdio://{base_path}/mcp-orders-server.py"),
            "price_monitor": MCPClient(f"stdio://{base_path}/mcp-price-monitor-server.py"),
        }
```

## Phase 2: Local Testing (Week 3)

### SQLite Development Database

#### Schema Setup
```sql
-- Initial schema for development
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE agent_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT UNIQUE NOT NULL,
    agent_type TEXT NOT NULL,
    model_slug TEXT DEFAULT 'claude-3-5-sonnet',
    system_prompt TEXT,
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE checkpoints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    checkpoint BLOB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Testing Strategy

#### Unit Tests
```python
# tests/test_agents.py
import pytest
from app.agents.products import ProductsAgent

async def test_products_agent():
    agent = ProductsAgent()
    result = await agent.process({
        "messages": ["Find product SKU ESP-001"]
    })
    assert result["success"] == True
```

#### Integration Tests
```python
# tests/test_mcp.py
async def test_mcp_connection():
    from app.tools.mcp_client import MCPManager
    manager = MCPManager()
    tools = await manager.servers["products"].get_tools()
    assert len(tools) > 0
```

#### End-to-End Tests
```python
# tests/test_orchestrator.py
async def test_full_conversation():
    orchestrator = Orchestrator()
    response = await orchestrator.run({
        "messages": ["Update price for SKU ESP-001 to 699.99"]
    })
    assert "updated" in response["messages"][-1].lower()
```

## Phase 3: Integration (Week 4)

### Frontend Connection

#### API Compatibility Layer
```python
# api/chat.py
from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

@router.post("/sse")
async def chat_sse(request: Request, body: dict):
    """Maintain exact same API as OpenAI SDK version"""
    
    async def generate():
        # Stream responses in same format
        yield {
            "event": "agent_message",
            "data": json.dumps({
                "agent": "Orchestrator",
                "message": "Processing...",
                "tokens": []
            })
        }
        
        # Run orchestrator
        async for chunk in orchestrator.stream(body):
            yield {
                "event": "agent_message",
                "data": json.dumps(chunk)
            }
    
    return EventSourceResponse(generate())
```

### Existing Component Integration

#### Price Monitor Connection
- Maintain same database tables
- Keep existing API endpoints
- No changes to cron jobs

#### Dashboard Analytics
- Preserve analytics endpoints
- Maintain same data format
- Keep existing visualizations

## Phase 4: Production Migration (Week 5)

### Database Migration

#### Step 1: Schema Export
```bash
# Export PostgreSQL schema
pg_dump -s espressobot_prod > schema.sql

# Create migration scripts
alembic init migrations
alembic revision --autogenerate -m "initial_migration"
```

#### Step 2: Data Migration
```python
# Dual-write during transition
class DualWriter:
    def write_message(self, message):
        # Write to both databases
        postgres_db.write(message)
        sqlite_db.write(message)
```

### Deployment Strategy

#### Blue-Green Deployment
1. Deploy LangGraph backend to production
2. Configure nginx for traffic splitting:
```nginx
upstream backend {
    server nodejs_backend:3000 weight=90;
    server langgraph_backend:8000 weight=10;
}
```

3. Gradually increase LangGraph weight:
   - Day 1: 10% traffic
   - Day 2: 25% traffic
   - Day 3: 50% traffic
   - Day 4: 75% traffic
   - Day 5: 100% traffic

#### Monitoring
```python
# Metrics collection
from prometheus_client import Counter, Histogram

request_count = Counter('requests_total', 'Total requests')
request_duration = Histogram('request_duration_seconds', 'Request duration')
```

## Phase 5: Optimization (Week 6)

### Performance Tuning
- Async execution optimization
- Connection pooling
- Cache implementation
- Query optimization

### Feature Enhancements
- Add LangGraph-specific features
- Implement advanced checkpointing
- Enable human-in-the-loop workflows

## Risk Mitigation

### Rollback Plan
1. Keep OpenAI SDK backend running
2. One-click switch via environment variable
3. Database replication for instant rollback
4. Feature flags for gradual rollout

### Testing Requirements
- [ ] All 14 agents migrated and tested
- [ ] MCP servers integration verified
- [ ] Frontend compatibility confirmed
- [ ] Performance benchmarks met
- [ ] Security audit completed

### Success Criteria
- Zero frontend changes required
- All existing features working
- Response time ≤ current system
- Token usage reduced by 30%+
- Error rate < 1%

## Support Materials

See `examples/` directory for:
- Agent implementation patterns
- MCP integration examples
- State management samples
- API endpoint templates