# LangGraph Architecture Design

## System Overview

The new architecture leverages LangGraph's graph-based orchestration to manage multi-agent workflows, replacing the OpenAI Agents SDK while maintaining full compatibility with existing systems.

## Core Architecture

### Graph-Based Orchestration

```python
# Conceptual flow
Start → Router → Agent Selection → Tool Execution → Response → End
         ↓
    State Management
         ↓
    Checkpointing
```

### State Management

LangGraph uses a shared state that flows through the graph:

```python
from typing import TypedDict, List, Dict, Any
from langgraph.graph import MessagesState

class ConversationState(MessagesState):
    """Enhanced state for our orchestrator"""
    # Core conversation data
    messages: List[Dict[str, Any]]
    conversation_id: str
    user_id: str
    
    # Agent routing
    current_agent: str
    agent_history: List[str]
    
    # Context and memory
    context: Dict[str, Any]
    memory_results: List[Dict[str, Any]]
    
    # Tool execution
    tool_calls: List[Dict[str, Any]]
    tool_results: Dict[str, Any]
    
    # Metadata
    token_count: int
    execution_time: float
    checkpoints: List[str]
```

## Agent Architecture

### Base Agent Pattern

Each agent follows a consistent pattern:

```python
from abc import ABC, abstractmethod
from langgraph.prebuilt import ToolNode

class BaseAgent(ABC):
    """Base class for all specialized agents"""
    
    def __init__(self, mcp_server: str, name: str):
        self.name = name
        self.mcp_client = MCPClient(f"stdio://{mcp_server}")
        self.tools = None
        
    async def initialize(self):
        """Load tools from MCP server"""
        self.tools = await self.mcp_client.get_tools()
        
    @abstractmethod
    async def process(self, state: ConversationState) -> ConversationState:
        """Process the current state"""
        pass
        
    def should_handle(self, state: ConversationState) -> bool:
        """Determine if this agent should handle the request"""
        # Implement routing logic
        pass
```

### Agent Specializations

#### 1. Products Agent
- **MCP Server**: `mcp-products-server.py`
- **Tools**: get_product, search_products, create_product, update_status
- **Expertise**: Product CRUD operations, search, status management

#### 2. Pricing Agent
- **MCP Server**: `mcp-pricing-server.py`
- **Tools**: update_pricing, bulk_price_update, update_costs
- **Expertise**: Price management, cost tracking, bulk operations

#### 3. Inventory Agent
- **MCP Server**: `mcp-inventory-server.py`
- **Tools**: manage_inventory_policy, manage_tags, manage_redirects
- **Expertise**: Stock management, product organization

#### 4. Sales Agent
- **MCP Server**: `mcp-sales-server.py`
- **Tools**: manage_miele_sales, manage_map_sales
- **Expertise**: MAP pricing, promotional campaigns

#### 5. Features Agent
- **MCP Server**: `mcp-features-server.py`
- **Tools**: manage_features_metaobjects, update_metafields, manage_variant_links
- **Expertise**: Product content, metafields, relationships

#### 6. Media Agent
- **MCP Server**: `mcp-media-server.py`
- **Tools**: add_product_images
- **Expertise**: Image management, media optimization

#### 7. Integrations Agent
- **MCP Server**: `mcp-integrations-server.py`
- **Tools**: SkuVault operations, send_review_request, perplexity_research
- **Expertise**: External system integration

#### 8. Product Management Agent
- **MCP Server**: `mcp-product-management-server.py`
- **Tools**: create_full_product, add_variants, create_combo, create_open_box
- **Expertise**: Complex product operations

#### 9. Utility Agent
- **MCP Server**: `mcp-utility-server.py`
- **Tools**: memory_operations
- **Expertise**: Knowledge management, memory search

## Orchestrator Design

### Main Orchestrator Graph

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

class EspressoBotOrchestrator:
    def __init__(self):
        self.agents = self._initialize_agents()
        self.graph = self._build_graph()
        self.checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
        
    def _build_graph(self):
        graph = StateGraph(ConversationState)
        
        # Add nodes
        graph.add_node("router", self.route_request)
        graph.add_node("memory_search", self.search_memory)
        graph.add_node("products_agent", self.agents["products"])
        graph.add_node("pricing_agent", self.agents["pricing"])
        # ... add all agents
        
        # Add edges
        graph.add_edge("START", "memory_search")
        graph.add_edge("memory_search", "router")
        graph.add_conditional_edges(
            "router",
            self.select_agent,
            {
                "products": "products_agent",
                "pricing": "pricing_agent",
                # ... map all agents
                "end": END
            }
        )
        
        # Compile with checkpointing
        return graph.compile(checkpointer=self.checkpointer)
```

### Routing Logic

```python
def select_agent(self, state: ConversationState) -> str:
    """Intelligent agent selection based on request"""
    
    last_message = state["messages"][-1]["content"]
    
    # Keyword-based routing (simplified)
    routing_rules = {
        "products": ["product", "sku", "search", "find"],
        "pricing": ["price", "cost", "discount"],
        "inventory": ["stock", "inventory", "quantity"],
        "sales": ["sale", "MAP", "promotion"],
        # ... more rules
    }
    
    for agent, keywords in routing_rules.items():
        if any(keyword in last_message.lower() for keyword in keywords):
            return agent
    
    # Use LLM for complex routing if needed
    return self.llm_route(state)
```

## MCP Integration Layer

### MCP Client Management

```python
class MCPClientManager:
    """Manages all MCP server connections"""
    
    def __init__(self):
        self.clients = {}
        self.base_path = "/home/pranav/espressobot/frontend/python-tools"
        
    async def initialize_all(self):
        """Initialize all MCP servers"""
        servers = [
            "mcp-products-server.py",
            "mcp-pricing-server.py",
            "mcp-inventory-server.py",
            # ... all servers
        ]
        
        for server in servers:
            name = server.replace("mcp-", "").replace("-server.py", "")
            self.clients[name] = await self._init_client(server)
    
    async def _init_client(self, server: str):
        """Initialize single MCP client"""
        client = MCPClient(f"stdio://{self.base_path}/{server}")
        await client.initialize()
        return client
```

## API Layer

### SSE Streaming

```python
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
import json

router = APIRouter()

@router.post("/api/agent/sse")
async def stream_chat(request: ChatRequest):
    """SSE endpoint matching current API"""
    
    async def event_generator():
        # Initialize orchestrator
        orchestrator = EspressoBotOrchestrator()
        
        # Create initial state
        state = ConversationState(
            messages=request.messages,
            conversation_id=request.conversation_id,
            user_id=request.user_id
        )
        
        # Stream execution
        async for event in orchestrator.graph.astream_events(
            state,
            version="v2"
        ):
            # Format for frontend compatibility
            if event["event"] == "on_chat_model_stream":
                yield {
                    "event": "agent_message",
                    "data": json.dumps({
                        "agent": event.get("name", "Assistant"),
                        "message": event["data"]["chunk"].content,
                        "tokens": [event["data"]["chunk"].content]
                    })
                }
    
    return EventSourceResponse(event_generator())
```

## Database Layer

### SQLAlchemy Models

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    title = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = relationship("Message", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")

class AgentConfig(Base):
    __tablename__ = "agent_configs"
    
    id = Column(Integer, primary_key=True)
    agent_name = Column(String(255), unique=True, nullable=False)
    agent_type = Column(String(100), nullable=False)
    model_slug = Column(String(255), default="claude-3-5-sonnet")
    system_prompt = Column(Text)
    is_active = Column(Boolean, default=True)
```

## Checkpointing and Recovery

### State Persistence

```python
from langgraph.checkpoint.sqlite import SqliteSaver

class CheckpointManager:
    """Manages conversation checkpoints"""
    
    def __init__(self, db_path: str = "checkpoints.db"):
        self.saver = SqliteSaver.from_conn_string(db_path)
        
    async def save_checkpoint(self, thread_id: str, state: dict):
        """Save conversation state"""
        await self.saver.aput(thread_id, state)
        
    async def load_checkpoint(self, thread_id: str):
        """Load conversation state"""
        return await self.saver.aget(thread_id)
        
    async def list_checkpoints(self, thread_id: str):
        """List all checkpoints for a thread"""
        return await self.saver.alist(thread_id)
```

### Error Recovery

```python
class ErrorRecovery:
    """Handles failures and recovery"""
    
    async def with_retry(self, func, max_retries: int = 3):
        """Execute with automatic retry"""
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
    async def recover_from_checkpoint(self, thread_id: str):
        """Recover conversation from last checkpoint"""
        checkpoint = await self.checkpoint_manager.load_checkpoint(thread_id)
        if checkpoint:
            return self.orchestrator.graph.invoke(
                checkpoint["state"],
                config={"configurable": {"thread_id": thread_id}}
            )
```

## Performance Optimizations

### Async Execution

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelExecutor:
    """Execute multiple operations in parallel"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    async def execute_parallel(self, tasks: List[Callable]):
        """Run tasks in parallel"""
        loop = asyncio.get_event_loop()
        futures = [
            loop.run_in_executor(self.executor, task)
            for task in tasks
        ]
        return await asyncio.gather(*futures)
```

### Caching Layer

```python
from functools import lru_cache
import redis

class CacheManager:
    """Manages response caching"""
    
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
        
    @lru_cache(maxsize=1000)
    def get_cached_response(self, key: str):
        """Get cached response"""
        return self.redis.get(key)
        
    def cache_response(self, key: str, value: str, ttl: int = 3600):
        """Cache response with TTL"""
        self.redis.setex(key, ttl, value)
```

## Security Considerations

### Authentication & Authorization

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate user authentication"""
    user = decode_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return user
```

### Input Validation

```python
from pydantic import BaseModel, validator

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    conversation_id: Optional[str]
    user_id: str
    
    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError("Messages cannot be empty")
        return v
```

## Monitoring & Observability

### Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
request_counter = Counter('requests_total', 'Total requests', ['agent', 'status'])
request_duration = Histogram('request_duration_seconds', 'Request duration', ['agent'])
active_conversations = Gauge('active_conversations', 'Number of active conversations')

# Collect metrics
@router.post("/api/agent/sse")
async def stream_chat(request: ChatRequest):
    with request_duration.labels(agent="orchestrator").time():
        # Process request
        pass
```

### Logging

```python
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)

# Use structured logging
logger.info("Agent execution", extra={
    "agent": agent_name,
    "conversation_id": conversation_id,
    "duration": duration,
    "tokens": token_count
})
```

## Migration Compatibility

### API Compatibility Matrix

| Current Endpoint | New Endpoint | Status |
|-----------------|--------------|--------|
| POST /api/agent/sse | POST /api/agent/sse | ✅ Identical |
| GET /api/conversations | GET /api/conversations | ✅ Identical |
| POST /api/memory | POST /api/memory | ✅ Identical |
| GET /api/dashboard | GET /api/dashboard | ✅ Identical |

### Event Format Compatibility

```javascript
// Current format (OpenAI SDK)
{
  event: "agent_message",
  data: {
    agent: "Orchestrator",
    message: "Processing...",
    tokens: ["token1", "token2"]
  }
}

// New format (LangGraph) - IDENTICAL
{
  event: "agent_message",
  data: {
    agent: "Orchestrator",
    message: "Processing...",
    tokens: ["token1", "token2"]
  }
}
```

This ensures zero changes required in the React frontend.