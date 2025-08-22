"""
Chat API using Optimized Progressive Orchestrator
Integrates with the new architecture while maintaining compatibility
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator
import logging
import uuid
import json
import time
import asyncio

from app.orchestrator_optimized import get_optimized_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessage(BaseModel):
    message: str
    thread_id: Optional[str] = None
    conversation_id: Optional[str] = None
    conv_id: Optional[str] = None
    user_id: Optional[str] = "1"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    agent: str = "orchestrator_optimized"
    performance_metrics: Optional[dict] = None

@router.post("/message")
async def send_message_optimized(chat_message: ChatMessage) -> ChatResponse:
    """
    Process a chat message using the optimized orchestrator
    """
    try:
        # Use thread_id, conversation_id, or conv_id - generate if none provided  
        thread_id = chat_message.thread_id or chat_message.conversation_id or chat_message.conv_id
        if not thread_id:
            thread_id = f"chat-optimized-{uuid.uuid4()}"
            logger.info(f"Generated new thread_id: {thread_id}")
        
        start_time = time.time()
        
        # Get the optimized orchestrator
        orchestrator = await get_optimized_orchestrator()
        
        # Process the message with the optimized orchestrator
        response_parts = []
        async for token in orchestrator.orchestrate(
            message=chat_message.message,
            thread_id=thread_id,
            user_id=chat_message.user_id
        ):
            response_parts.append(token)
        
        full_response = "".join(response_parts)
        duration = time.time() - start_time
        
        # Get performance metrics if available
        workflow_state = orchestrator.active_workflows.get(thread_id)
        performance_metrics = None
        if workflow_state:
            performance_metrics = {
                "duration_seconds": duration,
                "agent_calls": workflow_state.agent_call_count,
                "tokens_used": workflow_state.total_tokens_used,
                "state_transitions": workflow_state.current_state.value,
                "error_count": workflow_state.error_count,
                "retry_count": workflow_state.retry_count
            }
        
        return ChatResponse(
            response=full_response,
            conversation_id=thread_id,
            agent="orchestrator_optimized",
            performance_metrics=performance_metrics
        )
        
    except Exception as e:
        logger.error(f"Error in optimized chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def stream_message_optimized(chat_message: ChatMessage):
    """
    Stream chat response using the optimized orchestrator
    """
    async def generate():
        try:
            # Setup thread_id
            thread_id = chat_message.thread_id or chat_message.conversation_id or chat_message.conv_id
            if not thread_id:
                thread_id = f"stream-optimized-{uuid.uuid4()}"
            
            start_time = time.time()
            all_tokens = []
            
            # Get orchestrator and stream response
            orchestrator = await get_optimized_orchestrator()
            
            # Send initial event
            yield json.dumps({
                "event": "start",
                "thread_id": thread_id,
                "orchestrator": "optimized"
            }) + "\\n"
            
            # Stream tokens
            async for token in orchestrator.orchestrate(
                message=chat_message.message,
                thread_id=thread_id,
                user_id=chat_message.user_id
            ):
                all_tokens.append(token)
                
                # Send token event
                yield json.dumps({
                    "event": "token",
                    "token": token,
                    "thread_id": thread_id
                }) + "\\n"
                
                # Small delay for better streaming UX
                await asyncio.sleep(0.01)
            
            # Send completion event with metrics
            workflow_state = orchestrator.active_workflows.get(thread_id)
            completion_data = {
                "event": "complete",
                "thread_id": thread_id,
                "full_response": "".join(all_tokens),
                "duration_seconds": time.time() - start_time,
                "total_tokens": len(all_tokens)
            }
            
            if workflow_state:
                completion_data["performance_metrics"] = {
                    "agent_calls": workflow_state.agent_call_count,
                    "tokens_used": workflow_state.total_tokens_used,
                    "final_state": workflow_state.current_state.value,
                    "error_count": workflow_state.error_count,
                    "retry_count": workflow_state.retry_count
                }
            
            yield json.dumps(completion_data) + "\\n"
            
        except Exception as e:
            logger.error(f"Error in optimized streaming: {e}")
            yield json.dumps({
                "event": "error",
                "error": str(e),
                "thread_id": thread_id
            }) + "\\n"
    
    return StreamingResponse(generate(), media_type="text/plain")

@router.get("/health")
async def health_check_optimized():
    """Health check for optimized orchestrator"""
    try:
        orchestrator = await get_optimized_orchestrator()
        
        return {
            "status": "healthy",
            "orchestrator": "optimized",
            "agents_loaded": len(orchestrator.agents),
            "config": {
                "max_agent_calls": orchestrator.config.max_agent_calls_per_request,
                "agent_timeout": orchestrator.config.agent_timeout_seconds,
                "parallel_threshold": orchestrator.config.parallel_execution_threshold,
                "storage_type": orchestrator.config.state_storage_type
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/metrics")
async def get_orchestrator_metrics():
    """Get performance metrics from the optimized orchestrator"""
    try:
        orchestrator = await get_optimized_orchestrator()
        
        # Get active workflow stats
        active_workflows = len(orchestrator.active_workflows)
        
        return {
            "active_workflows": active_workflows,
            "total_agents": len(orchestrator.agents),
            "agent_names": list(orchestrator.agents.keys()),
            "config_summary": {
                "max_agent_calls": orchestrator.config.max_agent_calls_per_request,
                "timeout_seconds": orchestrator.config.agent_timeout_seconds,
                "max_retries": orchestrator.config.max_retries,
                "parallel_enabled": orchestrator.config.parallel_execution_threshold > 1,
                "persistence_enabled": orchestrator.config.persist_conversations
            }
        }
    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return {"error": str(e)}