#!/usr/bin/env python3
"""
Development server runner for LangGraph backend
"""
import asyncio
import uvicorn
import os
from dotenv import load_dotenv
from app.database.session import init_db

load_dotenv()

async def startup():
    """Initialize database and other startup tasks"""
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully")

def main():
    """Run the development server"""
    
    asyncio.run(startup())
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    print(f"Starting server on {host}:{port}")
    print(f"API docs available at http://{host}:{port}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()