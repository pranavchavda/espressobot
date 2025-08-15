"""
SSE Streaming Logs API for Live Agent Console
Provides real-time log streaming to frontend
"""
from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional
from collections import deque
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active connections
active_connections = {}

# Store recent logs in memory (last 1000 logs)
log_buffer = deque(maxlen=1000)

class LogBroadcaster:
    """Manages log broadcasting to all connected clients"""
    
    def __init__(self):
        self.connections = {}
        self.log_buffer = deque(maxlen=1000)
        
    def add_connection(self, connection_id: str, queue: asyncio.Queue):
        """Add a new connection"""
        self.connections[connection_id] = queue
        logger.info(f"Added log connection: {connection_id}")
        
    def remove_connection(self, connection_id: str):
        """Remove a connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            logger.info(f"Removed log connection: {connection_id}")
            
    async def broadcast(self, log_entry: dict):
        """Broadcast log entry to all connected clients"""
        # Add to buffer
        self.log_buffer.append(log_entry)
        
        # Send to all connected clients
        disconnected = []
        for conn_id, queue in self.connections.items():
            try:
                # Non-blocking put with timeout
                await asyncio.wait_for(queue.put(log_entry), timeout=0.1)
            except asyncio.TimeoutError:
                # Queue is full, skip this message
                pass
            except Exception as e:
                logger.error(f"Error broadcasting to {conn_id}: {e}")
                disconnected.append(conn_id)
                
        # Clean up disconnected clients
        for conn_id in disconnected:
            self.remove_connection(conn_id)
            
    def get_recent_logs(self, limit: int = 100) -> list:
        """Get recent logs from buffer"""
        return list(self.log_buffer)[-limit:]

# Global broadcaster instance
log_broadcaster = LogBroadcaster()

class LogCapture(logging.Handler):
    """Custom logging handler that captures logs and broadcasts them"""
    
    def emit(self, record):
        """Emit a log record"""
        try:
            # Determine category based on logger name
            category = "GENERAL"
            if "orchestrator" in record.name.lower():
                category = "ORCHESTRATOR"
            elif "agent" in record.name.lower():
                category = "AGENT"
            elif "memory" in record.name.lower():
                category = "MEMORY"
            elif "context" in record.name.lower():
                category = "CONTEXT"
            elif "mcp" in record.name.lower():
                category = "MCP"
            elif "learning" in record.name.lower():
                category = "LEARNING"
                
            # Create log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname.lower(),
                "category": category,
                "component": record.name,
                "message": record.getMessage(),
                "metadata": {}
            }
            
            # Add extra fields if present
            if hasattr(record, 'metadata'):
                log_entry["metadata"] = record.metadata
                
            # Broadcast to all connections
            asyncio.create_task(log_broadcaster.broadcast(log_entry))
            
        except Exception as e:
            # Don't let logging errors break the application
            pass

# Install the custom log handler
def install_log_capture():
    """Install the log capture handler on root logger"""
    handler = LogCapture()
    handler.setLevel(logging.DEBUG)
    
    # Add to specific loggers we care about
    loggers = [
        "app.orchestrator",
        "app.agents",
        "app.memory",
        "app.context_manager",
        "app.api",
        "app.services"
    ]
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
    logger.info("Log capture installed for live console")

# Install on module load
install_log_capture()

@router.get("/logs")
async def stream_logs(
    request: Request,
    token: Optional[str] = Query(None)
):
    """
    SSE endpoint for streaming logs to the frontend
    """
    # Simple auth check (you can enhance this)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    async def generate() -> AsyncGenerator[str, None]:
        connection_id = str(uuid.uuid4())
        queue = asyncio.Queue(maxsize=100)
        
        # Add connection to broadcaster
        log_broadcaster.add_connection(connection_id, queue)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'connectionId': connection_id})}\n\n"
            
            # Send recent logs
            recent_logs = log_broadcaster.get_recent_logs(50)
            for log in recent_logs:
                yield f"data: {json.dumps(log)}\n\n"
            
            # Stream new logs
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                    
                try:
                    # Wait for new log with timeout
                    log_entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(log_entry)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    
        except asyncio.CancelledError:
            pass
        finally:
            # Clean up connection
            log_broadcaster.remove_connection(connection_id)
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/log")
async def post_log(request: Request):
    """
    Endpoint to post logs from frontend or other sources
    """
    try:
        log_data = await request.json()
        
        # Create log entry
        log_entry = {
            "timestamp": log_data.get("timestamp", datetime.utcnow().isoformat()),
            "level": log_data.get("level", "info"),
            "category": log_data.get("category", "FRONTEND"),
            "component": log_data.get("component", "frontend"),
            "message": log_data.get("message", ""),
            "metadata": log_data.get("metadata", {})
        }
        
        # Broadcast to all connections
        await log_broadcaster.broadcast(log_entry)
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"Error posting log: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# Helper function for manual logging
async def log_to_console(message: str, level: str = "info", category: str = "GENERAL", metadata: dict = None):
    """Helper function to manually log to the live console"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "category": category,
        "component": "manual",
        "message": message,
        "metadata": metadata or {}
    }
    await log_broadcaster.broadcast(log_entry)