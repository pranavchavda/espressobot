from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting EspressoBot LangGraph Backend...")
    yield
    logger.info("Shutting down EspressoBot LangGraph Backend...")

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

from app.api import chat, conversations, auth_proxy, chat_enhanced, agent_management, memory_enhanced, dashboard, price_monitor

app.include_router(chat.router, prefix="/api/agent")
app.include_router(chat_enhanced.router, prefix="/api/agent/v2")
app.include_router(conversations.router, prefix="/api/conversations")
app.include_router(auth_proxy.router)  # Auth proxy includes its own /api/auth prefix
app.include_router(agent_management.router)  # Agent management API
app.include_router(memory_enhanced.router, prefix="/api/memory")  # Enhanced memory management API

# Enable dashboard router
app.include_router(dashboard.router, prefix="/api/dashboard")

# Enable price monitor router
app.include_router(price_monitor.router)

# Temporarily disable other routers that depend on SQLAlchemy
# app.include_router(auth.router, prefix="/api/auth")