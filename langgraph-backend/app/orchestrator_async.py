"""
Async Background Task Manager
Wraps the main orchestrator with background task management:
User → Immediate Task ID → Background Processing → WebSocket Progress Updates
"""
import asyncio
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator
from enum import Enum
from dataclasses import dataclass, field
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskProgress:
    task_id: str
    status: TaskStatus
    message: str = ""
    response: str = ""
    progress: float = 0.0  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    thread_id: Optional[str] = None

class AsyncOrchestrator:
    """
    Background task manager that wraps the main orchestrator with:
    - Async task execution and progress tracking
    - WebSocket broadcasting for real-time updates
    - Task cancellation and interruption support
    - Memory processing in background
    """
    
    def __init__(self):
        self.tasks: Dict[str, TaskProgress] = {}
        self.websockets: Dict[str, List[WebSocket]] = {}  # thread_id -> websockets
        self.background_tasks: Dict[str, asyncio.Task] = {}
        
        # Import memory manager lazily to avoid circular imports
        self._memory_manager = None
        
    @property 
    def memory_manager(self):
        if self._memory_manager is None:
            from app.memory.postgres_memory_manager_v2 import SimpleMemoryManager
            self._memory_manager = SimpleMemoryManager()
        return self._memory_manager
    
    async def start_task(self, message: str, thread_id: str = None, user_id: str = "1") -> str:
        """
        Start a background task and return task ID immediately
        Auto-cancels any existing running tasks for the same thread
        """
        task_id = str(uuid.uuid4())
        if not thread_id:
            thread_id = f"chat-{task_id}"
        
        # Cancel any existing running tasks for this thread
        await self._cancel_thread_tasks(thread_id, reason="New task started")
            
        # Create task progress tracker
        task_progress = TaskProgress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"Starting to process: {message[:50]}...",
            thread_id=thread_id  # Store thread_id for cancellation
        )
        self.tasks[task_id] = task_progress
        
        # Start background processing
        background_task = asyncio.create_task(
            self._process_task_async(task_id, message, thread_id, user_id)
        )
        self.background_tasks[task_id] = background_task
        
        logger.info(f"Started background task {task_id} for thread {thread_id}")
        return task_id
    
    async def _process_task_async(self, task_id: str, message: str, thread_id: str, user_id: str):
        """
        Process the task in background and update progress
        """
        try:
            task_progress = self.tasks[task_id]
            task_progress.status = TaskStatus.RUNNING
            task_progress.message = "Starting main orchestrator..."
            task_progress.updated_at = datetime.utcnow()
            
            await self._broadcast_update(thread_id, task_progress)
            
            # Use the main orchestrator for processing (it handles all routing and agent calls)
            task_progress.progress = 0.2
            task_progress.message = "Processing with main orchestrator..."
            await self._broadcast_update(thread_id, task_progress)
            
            # Import and use the main orchestrator
            from app.orchestrator import orchestrator
            
            # The orchestrator returns a generator, so we need to consume it
            response_parts = []
            try:
                async for token in orchestrator.orchestrate(message, thread_id, user_id):
                    # Check if task was cancelled during processing
                    if task_progress.status == TaskStatus.CANCELLED:
                        logger.info(f"Task {task_id} was cancelled during orchestrator streaming")
                        # Return partial response if we have any
                        task_progress.response = "".join(response_parts).strip() if response_parts else ""
                        task_progress.message = "Task was interrupted"
                        await self._broadcast_update(thread_id, task_progress)
                        return
                    
                    response_parts.append(token)
                    # Update progress as we get tokens
                    current_progress = 0.2 + (len(response_parts) / 100) * 0.7  # Progress from 0.2 to 0.9
                    task_progress.progress = min(current_progress, 0.9)
                    if len(response_parts) % 10 == 0:  # Update every 10 tokens to avoid spam
                        await self._broadcast_update(thread_id, task_progress)
            except asyncio.CancelledError:
                logger.info(f"Task {task_id} was cancelled via asyncio.CancelledError")
                # Save partial response
                task_progress.response = "".join(response_parts).strip() if response_parts else ""
                task_progress.message = "Task was interrupted"
                task_progress.status = TaskStatus.CANCELLED
                await self._broadcast_update(thread_id, task_progress)
                raise  # Re-raise to properly handle cancellation
            
            final_response = "".join(response_parts).strip()
            
            # Step 4: Complete task
            task_progress.status = TaskStatus.COMPLETED
            task_progress.response = final_response
            task_progress.progress = 1.0
            task_progress.message = "Task completed successfully"
            task_progress.updated_at = datetime.utcnow()
            
            await self._broadcast_update(thread_id, task_progress)
            
            # Background memory processing (non-blocking)
            asyncio.create_task(self._process_memory_async(message, final_response, user_id))
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}", exc_info=True)
            task_progress = self.tasks[task_id]
            task_progress.status = TaskStatus.FAILED
            task_progress.error = str(e)
            task_progress.message = f"Task failed: {str(e)[:100]}"
            task_progress.updated_at = datetime.utcnow()
            await self._broadcast_update(thread_id, task_progress)
        
        finally:
            # Clean up background task reference
            if task_id in self.background_tasks:
                del self.background_tasks[task_id]
    
    async def _broadcast_update(self, thread_id: str, task_progress: TaskProgress):
        """
        Broadcast task update to connected WebSockets
        """
        if thread_id in self.websockets:
            message = {
                "type": "task_update",
                "task_id": task_progress.task_id,
                "status": task_progress.status.value,
                "message": task_progress.message,
                "progress": task_progress.progress,
                "response": task_progress.response,
                "updated_at": task_progress.updated_at.isoformat()
            }
            
            # Send to all connected websockets for this thread
            websockets_to_remove = []
            for ws in self.websockets[thread_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    websockets_to_remove.append(ws)
            
            # Clean up disconnected websockets
            for ws in websockets_to_remove:
                self.websockets[thread_id].remove(ws)
    
    async def _process_memory_async(self, message: str, response: str, user_id: str):
        """
        Process memory extraction in background (non-blocking)
        """
        try:
            # This runs in background and doesn't block the main response
            if self.memory_manager:
                from app.memory.memory_persistence import MemoryExtractionService
                from langchain_core.messages import HumanMessage, AIMessage
                
                extraction_service = MemoryExtractionService()
                logger.info("Memory extraction service initialized")
                
                # Build conversation for extraction using proper message objects
                messages_for_extraction = [
                    HumanMessage(content=message),
                    AIMessage(content=response)
                ]
                
                logger.info(f"Extracting memories from conversation: User: {message[:100]}... Assistant: {response[:100]}...")
                
                # Extract memories
                extracted_memories = await extraction_service.extract_memories_from_conversation(
                    messages_for_extraction, user_id
                )
                
                logger.info(f"Extracted {len(extracted_memories)} memories")
                
                # Save extracted memories
                saved_count = 0
                for mem in extracted_memories:
                    try:
                        memory_id = await self.memory_manager.store_memory(mem)
                        if memory_id:
                            saved_count += 1
                            logger.info(f"💾 Saved memory #{memory_id}: {mem.content[:50]}...")
                    except Exception as e:
                        logger.warning(f"Failed to save memory: {e}")
                
                if saved_count > 0:
                    logger.info(f"✅ Extracted and saved {saved_count} memories from conversation")
                else:
                    logger.info("No memories extracted or saved")
                    
        except Exception as e:
            logger.warning(f"Background memory processing failed: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[TaskProgress]:
        """Get current status of a task"""
        return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id in self.background_tasks:
            task = self.background_tasks[task_id]
            if not task.done():
                task.cancel()
                if task_id in self.tasks:
                    self.tasks[task_id].status = TaskStatus.CANCELLED
                    self.tasks[task_id].message = "Task cancelled by user"
                return True
        return False
    
    async def _cancel_thread_tasks(self, thread_id: str, reason: str = "Thread interrupted") -> int:
        """
        Cancel all running tasks for a specific thread
        Returns number of tasks cancelled
        """
        cancelled_count = 0
        
        # Find all tasks for this thread
        thread_tasks = []
        for task_id, task_progress in self.tasks.items():
            if task_progress.thread_id == thread_id and task_progress.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                thread_tasks.append((task_id, task_progress))
        
        # Cancel each task
        for task_id, task_progress in thread_tasks:
            if await self.cancel_task(task_id):
                task_progress.message = f"Interrupted: {reason}"
                task_progress.updated_at = datetime.utcnow()
                cancelled_count += 1
                logger.info(f"Cancelled task {task_id} for thread {thread_id}: {reason}")
        
        if cancelled_count > 0:
            logger.info(f"Cancelled {cancelled_count} running tasks for thread {thread_id}")
        
        return cancelled_count
    
    async def interrupt_thread(self, thread_id: str) -> Dict[str, Any]:
        """
        Interrupt all running tasks for a thread and return their partial results
        """
        cancelled_count = await self._cancel_thread_tasks(thread_id, "User interrupt")
        
        # Collect any partial results from cancelled tasks
        partial_results = []
        for task_id, task_progress in self.tasks.items():
            if (task_progress.thread_id == thread_id and 
                task_progress.status == TaskStatus.CANCELLED and 
                (task_progress.agent_results or task_progress.response)):
                
                partial_results.append({
                    "task_id": task_id,
                    "partial_response": task_progress.response,
                    "agent_results": task_progress.agent_results,
                    "progress": task_progress.progress
                })
        
        return {
            "cancelled_tasks": cancelled_count,
            "partial_results": partial_results,
            "message": f"Interrupted {cancelled_count} running task(s)" if cancelled_count > 0 else "No running tasks to interrupt"
        }
    
    async def add_websocket(self, thread_id: str, websocket: WebSocket):
        """Add WebSocket for real-time updates"""
        if thread_id not in self.websockets:
            self.websockets[thread_id] = []
        self.websockets[thread_id].append(websocket)
    
    async def remove_websocket(self, thread_id: str, websocket: WebSocket):
        """Remove WebSocket"""
        if thread_id in self.websockets and websocket in self.websockets[thread_id]:
            self.websockets[thread_id].remove(websocket)
            if not self.websockets[thread_id]:
                del self.websockets[thread_id]

# Singleton instance
async_orchestrator = AsyncOrchestrator()

async def get_async_orchestrator() -> AsyncOrchestrator:
    """Get the async orchestrator instance"""
    return async_orchestrator