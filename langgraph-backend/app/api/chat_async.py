"""
Async Chat API using Background Task Orchestrator
Implements: User → Immediate Response → Background Processing → WebSocket Updates
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging
import uuid
import time

from app.orchestrator_async import get_async_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

class AsyncChatMessage(BaseModel):
    message: str
    thread_id: Optional[str] = None
    conversation_id: Optional[str] = None  # Also accept conversation_id
    conv_id: Optional[str] = None  # Frontend uses conv_id
    user_id: Optional[str] = "1"

class AsyncChatResponse(BaseModel):
    task_id: str
    conversation_id: str
    status: str
    message: str
    websocket_url: str

@router.post("/async/message")
async def send_async_message(chat_message: AsyncChatMessage) -> AsyncChatResponse:
    """
    Process a chat message asynchronously - returns immediately with task ID
    """
    try:
        # Use thread_id, conversation_id, or conv_id - generate if none provided  
        thread_id = chat_message.thread_id or chat_message.conversation_id or chat_message.conv_id
        if not thread_id:
            thread_id = f"chat-{uuid.uuid4()}"
            logger.info(f"Generated new thread_id: {thread_id}")
        else:
            logger.info(f"Using thread_id: {thread_id}")
        
        # Get the async orchestrator
        orchestrator = await get_async_orchestrator()
        
        # Start background task - this returns immediately
        task_id = await orchestrator.start_task(
            message=chat_message.message,
            thread_id=thread_id,
            user_id=chat_message.user_id
        )
        
        return AsyncChatResponse(
            task_id=task_id,
            conversation_id=thread_id,
            status="started",
            message=f"Processing your request in background. Task ID: {task_id}",
            websocket_url=f"/api/ws/{thread_id}"
        )
        
    except Exception as e:
        logger.error(f"Error starting async message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/async/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Get current status of a background task
    """
    try:
        orchestrator = await get_async_orchestrator()
        task_progress = orchestrator.get_task_status(task_id)
        
        if not task_progress:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return {
            "task_id": task_id,
            "status": task_progress.status.value,
            "message": task_progress.message,
            "response": task_progress.response,
            "progress": task_progress.progress,
            "created_at": task_progress.created_at.isoformat(),
            "updated_at": task_progress.updated_at.isoformat(),
            "agent_results": task_progress.agent_results,
            "error": task_progress.error
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/async/task/{task_id}")
async def cancel_task(task_id: str):
    """
    Cancel a running background task
    """
    try:
        orchestrator = await get_async_orchestrator()
        cancelled = await orchestrator.cancel_task(task_id)
        
        if not cancelled:
            raise HTTPException(status_code=404, detail="Task not found or already completed")
        
        return {"message": f"Task {task_id} cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/async/tasks/thread/{thread_id}")
async def get_thread_tasks(thread_id: str):
    """
    Get all tasks for a specific thread/conversation
    """
    try:
        orchestrator = await get_async_orchestrator()
        
        # Filter tasks by thread_id from task progress
        thread_tasks = []
        for task_id, task_progress in orchestrator.tasks.items():
            # We need to store thread_id in task progress to make this work
            # For now, return all tasks - can be enhanced later
            thread_tasks.append({
                "task_id": task_id,
                "status": task_progress.status.value,
                "message": task_progress.message,
                "response": task_progress.response,
                "progress": task_progress.progress,
                "created_at": task_progress.created_at.isoformat(),
                "updated_at": task_progress.updated_at.isoformat()
            })
        
        return {"thread_id": thread_id, "tasks": thread_tasks}
        
    except Exception as e:
        logger.error(f"Error getting thread tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/async/test")
async def test_async_endpoint():
    """
    Test endpoint to verify async processing works
    """
    try:
        orchestrator = await get_async_orchestrator()
        
        # Start a test task
        task_id = await orchestrator.start_task(
            message="Test async processing",
            thread_id="test-thread",
            user_id="test-user"
        )
        
        return {
            "message": "Async test started",
            "task_id": task_id,
            "status": "Test task created successfully",
            "websocket_url": "/api/ws/test-thread"
        }
        
    except Exception as e:
        logger.error(f"Error in async test: {e}")
        raise HTTPException(status_code=500, detail=str(e))