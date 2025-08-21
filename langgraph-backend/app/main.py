from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv
from app.db.connection_pool import get_database_pool

load_dotenv()

logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EspressoBot LangGraph Backend...")
    
    # Initialize database connection pool
    db_pool = get_database_pool()
    try:
        await db_pool.initialize()
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database pool: {e}")
        raise
    
    yield
    
    # Clean shutdown - close database pool
    logger.info("Shutting down EspressoBot LangGraph Backend...")
    try:
        await db_pool.close()
        logger.info("Database connection pool closed successfully")
    except Exception as e:
        logger.warning(f"Error closing database pool: {e}")

app = FastAPI(
    title="EspressoBot LangGraph Backend",
    version="1.0.0",
    description="LangGraph-powered backend for EspressoBot",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",  # Vite dev server
        "http://localhost:5174",  # Alternative Vite port
        os.getenv("FRONTEND_URL", "http://localhost:3000")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "EspressoBot LangGraph Backend", "status": "operational"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

from app.api import chat, chat_async, websocket, conversations, auth_proxy, agent_management, memory_enhanced, dashboard, price_monitor, dynamic_agents, user_mcp_servers, orchestrator_admin, logs_stream, sandbox, scratchpad, profile, cli_auth

# Main chat endpoint using the orchestrator
app.include_router(chat.router, prefix="/api/agent")

# Async chat endpoints with background processing
app.include_router(chat_async.router, prefix="/api/agent")

# WebSocket endpoints for real-time updates
app.include_router(websocket.router, prefix="/api")

# Add logs streaming for live console
app.include_router(logs_stream.router, prefix="/api/agent")
app.include_router(conversations.router, prefix="/api/conversations")
app.include_router(auth_proxy.router)  # Auth proxy includes its own /api/auth prefix
app.include_router(agent_management.router)  # Agent management API
app.include_router(memory_enhanced.router, prefix="/api/memory")  # Enhanced memory management API

# Enable dashboard router
app.include_router(dashboard.router, prefix="/api/dashboard")

# Enable price monitor router
app.include_router(price_monitor.router)
app.include_router(price_monitor.shopify_sync_safe_router)

# Dynamic agents and MCP servers
app.include_router(dynamic_agents.router)  # Dynamic agent management
app.include_router(user_mcp_servers.router)  # User MCP server management
app.include_router(orchestrator_admin.router)  # Orchestrator admin endpoints
app.include_router(sandbox.router, prefix="/api")  # Sandbox file serving
app.include_router(scratchpad.router, prefix="/api")  # Scratchpad functionality
app.include_router(profile.router, prefix="/api")  # User profile management
app.include_router(cli_auth.router)  # CLI authentication support

# Temporarily disable other routers that depend on SQLAlchemy
# app.include_router(auth.router, prefix="/api/auth")
