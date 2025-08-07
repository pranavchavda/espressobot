"""Memory API endpoints for conversation history and search"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

from ..memory.memory_persistence import get_memory_node
from ..memory import Memory, PromptFragment, ContextTier

logger = logging.getLogger(__name__)
router = APIRouter()

class ConversationHistoryRequest(BaseModel):
    thread_id: str
    limit: Optional[int] = 50

class SearchMemoryRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None
    user_id: Optional[str] = None
    limit: Optional[int] = 10

@router.get("/conversations/{thread_id}/history")
async def get_conversation_history(
    thread_id: str,
    limit: Optional[int] = Query(50, description="Maximum number of messages to return")
):
    """Get conversation history for a specific thread"""
    try:
        from app.api.chat import get_orchestrator
        orchestrator = get_orchestrator()
        
        # Get the checkpoint for this thread
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = orchestrator.checkpointer.get(config)
        
        if not checkpoint:
            return {"messages": [], "thread_id": thread_id}
        
        # Extract messages from checkpoint
        messages = checkpoint.get("channel_values", {}).get("messages", [])
        
        # Convert to serializable format
        formatted_messages = []
        for msg in messages[-limit:]:  # Get last N messages
            formatted_messages.append({
                "type": msg.__class__.__name__.replace("Message", "").lower(),
                "content": msg.content,
                "timestamp": getattr(msg, "timestamp", None),
                "metadata": getattr(msg, "metadata", {})
            })
        
        return {
            "thread_id": thread_id,
            "messages": formatted_messages,
            "total_messages": len(messages)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving conversation history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations")
async def list_conversations(
    limit: Optional[int] = Query(20, description="Maximum number of conversations to return")
):
    """List all conversation threads"""
    try:
        from app.api.chat import get_orchestrator
        orchestrator = get_orchestrator()
        
        # Get all checkpoints (threads)
        threads = []
        
        # This depends on the checkpointer implementation
        # For SQLite/Postgres, we'd query the database
        # For now, return empty list as MemorySaver doesn't support listing
        
        return {"conversations": threads}
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{thread_id}")
async def clear_conversation(thread_id: str):
    """Clear a specific conversation thread"""
    try:
        from app.api.chat import get_orchestrator
        orchestrator = get_orchestrator()
        
        # Clear the checkpoint for this thread
        config = {"configurable": {"thread_id": thread_id}}
        
        # This depends on checkpointer implementation
        # Most checkpointers don't have a delete method
        # We'd need to implement this in our custom checkpointers
        
        return {"success": True, "thread_id": thread_id}
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New memory management endpoints

class MemorySearchRequest(BaseModel):
    query: str
    user_id: str
    limit: Optional[int] = 10
    similarity_threshold: Optional[float] = 0.7

class CreateMemoryRequest(BaseModel):
    user_id: str
    content: str
    category: Optional[str] = "general"
    importance: Optional[float] = 1.0
    metadata: Optional[Dict[str, Any]] = {}

class CreatePromptFragmentRequest(BaseModel):
    category: str
    content: str
    priority: Optional[int] = 0
    agent_type: Optional[str] = None
    context_tier: Optional[str] = "standard"
    tags: Optional[List[str]] = []

@router.post("/memory/search")
async def search_memories(request: MemorySearchRequest):
    """Search through user memories using semantic similarity"""
    try:
        memory_node = get_memory_node()
        
        results = await memory_node.search_user_memories(
            user_id=request.user_id,
            query=request.query,
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "user_id": request.user_id,
            "results": results,
            "count": len(results)
        }
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/create")
async def create_memory(request: CreateMemoryRequest):
    """Create a new memory for a user"""
    try:
        memory_node = get_memory_node()
        await memory_node.initialize()
        
        memory = Memory(
            user_id=request.user_id,
            content=request.content,
            category=request.category,
            importance_score=request.importance,
            metadata=request.metadata
        )
        
        memory_id = await memory_node.memory_manager.store_memory(memory)
        
        return {
            "success": True,
            "memory_id": memory_id,
            "message": "Memory created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/stats/{user_id}")
async def get_memory_stats(user_id: str):
    """Get memory statistics for a user"""
    try:
        memory_node = get_memory_node()
        stats = await memory_node.get_memory_stats(user_id)
        
        return {
            "user_id": user_id,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting memory stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/fragments")
async def create_prompt_fragment(request: CreatePromptFragmentRequest):
    """Create a new prompt fragment"""
    try:
        memory_node = get_memory_node()
        await memory_node.initialize()
        
        fragment = PromptFragment(
            category=request.category,
            content=request.content,
            priority=request.priority,
            agent_type=request.agent_type,
            context_tier=request.context_tier,
            tags=request.tags or []
        )
        
        fragment_id = await memory_node.prompt_assembler.store_prompt_fragment(fragment)
        
        return {
            "success": True,
            "fragment_id": fragment_id,
            "message": "Prompt fragment created successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating prompt fragment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/fragments/stats")
async def get_fragment_stats():
    """Get prompt fragment statistics"""
    try:
        memory_node = get_memory_node()
        await memory_node.initialize()
        
        stats = await memory_node.prompt_assembler.get_fragment_stats()
        
        return {
            "fragment_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting fragment stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/memory/performance")
async def get_performance_stats():
    """Get memory system performance statistics"""
    try:
        memory_node = get_memory_node()
        await memory_node.initialize()
        
        performance = memory_node.memory_manager.get_performance_stats()
        
        return {
            "performance": performance
        }
        
    except Exception as e:
        logger.error(f"Error getting performance stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/cleanup")
async def cleanup_old_memories(
    days_old: Optional[int] = Query(90, description="Delete memories older than this many days"),
    min_access_count: Optional[int] = Query(1, description="Only delete memories accessed fewer than this many times")
):
    """Clean up old, unused memories"""
    try:
        memory_node = get_memory_node()
        await memory_node.initialize()
        
        deleted_count = await memory_node.memory_manager.cleanup_old_memories(
            days_old=days_old,
            min_access_count=min_access_count
        )
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} old memories"
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory/search")
async def search_memory(request: SearchMemoryRequest):
    """Search through conversation memories (legacy endpoint)"""
    try:
        # Redirect to new search endpoint
        if hasattr(request, 'user_id') and request.user_id:
            search_request = MemorySearchRequest(
                query=request.query,
                user_id=request.user_id,
                limit=request.limit
            )
            return await search_memories(search_request)
        else:
            return {
                "query": request.query,
                "results": [],
                "message": "user_id required for memory search"
            }
        
    except Exception as e:
        logger.error(f"Error searching memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))