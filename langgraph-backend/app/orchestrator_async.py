"""
Async Background Task Orchestrator
Implements: User → Immediate Response → Background Processing → WebSocket Updates
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

class AsyncOrchestrator:
    """
    Async orchestrator that processes requests in background tasks
    and provides real-time updates via WebSockets
    """
    
    def __init__(self):
        self.tasks: Dict[str, TaskProgress] = {}
        self.websockets: Dict[str, List[WebSocket]] = {}  # thread_id -> websockets
        self.background_tasks: Dict[str, asyncio.Task] = {}
        
        # Import agents lazily to avoid circular imports
        self._agents = None
        self._memory_manager = None
        
    @property
    def agents(self):
        if self._agents is None:
            from app.agents.registry import get_all_agents
            self._agents = get_all_agents()
        return self._agents
    
    @property 
    def memory_manager(self):
        if self._memory_manager is None:
            from app.memory.postgres_memory_manager_v2 import PostgresMemoryManager
            self._memory_manager = PostgresMemoryManager()
        return self._memory_manager
    
    async def start_task(self, message: str, thread_id: str = None, user_id: str = "1") -> str:
        """
        Start a background task and return task ID immediately
        """
        task_id = str(uuid.uuid4())
        if not thread_id:
            thread_id = f"chat-{task_id}"
            
        # Create task progress tracker
        task_progress = TaskProgress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message=f"Starting to process: {message[:50]}..."
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
            task_progress.message = "Analyzing request and planning agents..."
            task_progress.updated_at = datetime.utcnow()
            
            await self._broadcast_update(thread_id, task_progress)
            
            # Use the main orchestrator for processing (it handles agent routing internally)
            task_progress.progress = 0.2
            task_progress.message = "Processing with orchestrator..."
            await self._broadcast_update(thread_id, task_progress)
            
            # Import and use the main orchestrator
            from app.orchestrator import orchestrator
            
            # The orchestrator returns a generator, so we need to consume it
            response_parts = []
            async for token in orchestrator.orchestrate(message, thread_id, user_id):
                response_parts.append(token)
                # Update progress as we get tokens
                current_progress = 0.2 + (len(response_parts) / 100) * 0.7  # Progress from 0.2 to 0.9
                task_progress.progress = min(current_progress, 0.9)
                if len(response_parts) % 10 == 0:  # Update every 10 tokens to avoid spam
                    await self._broadcast_update(thread_id, task_progress)
            
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
    
    async def _plan_agents(self, message: str) -> List[str]:
        """
        Use LLM intelligence to determine which agents to use
        """
        from app.config.agent_model_manager import agent_model_manager
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # Get a fast model for routing decisions
        routing_model = agent_model_manager.get_model_for_agent("utility")  # Use any available model
        
        routing_prompt = """You are an intelligent agent router for EspressoBot, an e-commerce management system.

Based on the user's message, determine which specialized agents should handle the request. Return ONLY a JSON array of agent names.

Available agents:
- "orders": Sales analytics, revenue reports, order tracking, daily sales
- "products": Product search, details, inventory status, stock levels  
- "pricing": Price updates, discounts, MAP sales, cost management
- "ga4_analytics": Website traffic, user behavior, GA4 analytics
- "utility": Web scraping, research, general utilities, calculations

Examples:
User: "check today sales" → ["orders"]
User: "what's the price of espresso machine" → ["products"]
User: "update price to $199" → ["pricing"] 
User: "website traffic today" → ["ga4_analytics"]
User: "sales and traffic today" → ["orders", "ga4_analytics"]
User: "scrape competitor pricing" → ["utility"]

Return only the JSON array, nothing else."""

        try:
            messages = [
                SystemMessage(content=routing_prompt),
                HumanMessage(content=f"User message: {message}")
            ]
            
            response = await routing_model.ainvoke(messages)
            
            # Parse the JSON response
            import json
            agents_to_call = json.loads(response.content.strip())
            
            # Validate agent names
            valid_agents = []
            for agent in agents_to_call:
                if agent in self.agents:
                    valid_agents.append(agent)
            
            # Fallback to utility if no valid agents
            if not valid_agents:
                valid_agents = ['utility']
                
            logger.info(f"LLM routing selected agents: {valid_agents} for message: {message[:50]}...")
            return valid_agents
            
        except Exception as e:
            logger.error(f"LLM routing failed, falling back to utility: {e}")
            return ['utility']
    
    async def _execute_agents_parallel(self, agent_names: List[str], message: str, task_progress: TaskProgress, thread_id: str) -> Dict[str, Any]:
        """
        Execute agents in parallel for maximum speed
        """
        agent_results = {}
        
        # Create agent tasks
        agent_tasks = []
        for agent_name in agent_names:
            if agent_name in self.agents:
                agent_task = asyncio.create_task(
                    self._call_agent_async(agent_name, message, task_progress, thread_id)
                )
                agent_tasks.append((agent_name, agent_task))
        
        # Wait for all agents to complete
        for agent_name, agent_task in agent_tasks:
            try:
                result = await agent_task
                agent_results[agent_name] = result
                logger.info(f"Agent {agent_name} completed successfully")
            except Exception as e:
                logger.error(f"Agent {agent_name} failed: {e}")
                agent_results[agent_name] = {"error": str(e)}
        
        return agent_results
    
    async def _call_agent_async(self, agent_name: str, message: str, task_progress: TaskProgress, thread_id: str) -> Dict[str, Any]:
        """
        Call a single agent asynchronously
        """
        agent = self.agents[agent_name]
        
        # Update progress
        task_progress.message = f"Calling {agent_name} agent..."
        await self._broadcast_update(thread_id, task_progress)
        
        # Call agent
        result = await agent.process_async(message)
        
        # Update progress
        task_progress.agent_results[agent_name] = result
        task_progress.message = f"Completed {agent_name} agent"
        await self._broadcast_update(thread_id, task_progress)
        
        return result
    
    async def _synthesize_response(self, message: str, agent_results: Dict[str, Any]) -> str:
        """
        Synthesize final response from agent results
        """
        if not agent_results:
            return "I wasn't able to process your request with any agents."
        
        # Simple synthesis for now - can be enhanced with LLM
        response_parts = []
        
        for agent_name, result in agent_results.items():
            if isinstance(result, dict) and "error" not in result:
                if "content" in result:
                    response_parts.append(f"**{agent_name.title()} Agent:**\n{result['content']}")
                elif "response" in result:
                    response_parts.append(f"**{agent_name.title()} Agent:**\n{result['response']}")
        
        if response_parts:
            return "\n\n".join(response_parts)
        else:
            return "I processed your request but didn't get usable results from the agents."
    
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
                await self.memory_manager.extract_and_store_memories(
                    user_message=message,
                    assistant_response=response,
                    user_id=user_id
                )
                logger.info("Memory extraction completed in background")
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