from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
import json
import logging
import asyncio
import time
from app.orchestrator import Orchestrator
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

_orchestrator: Optional[Orchestrator] = None

def get_orchestrator() -> Orchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    conv_id: Optional[str] = None  # Frontend uses conv_id
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None
    image: Optional[Dict[str, Any]] = None  # For image attachments
    file: Optional[Dict[str, Any]] = None   # For file attachments

@router.post("/stream")
async def chat_stream(request: ChatRequest):
    """HTTP streaming endpoint using NDJSON (newline-delimited JSON)"""
    
    orchestrator = get_orchestrator()
    
    # Use conv_id if provided (frontend compatibility)
    conversation_id = request.conv_id or request.conversation_id
    # Use conversation_id as thread_id for LangGraph checkpointing
    thread_id = request.thread_id or conversation_id or f"chat-{int(time.time())}"
    
    async def generate():
        try:
            # Send conversation ID first so frontend knows what thread is being used
            yield json.dumps({
                "event": "conversation_id",
                "conv_id": thread_id,
                "thread_id": thread_id
            }) + "\n"
            
            # Send initial message
            yield json.dumps({
                "event": "agent_message",
                "agent": "Orchestrator",
                "message": "Processing your request...",
                "tokens": []
            }) + "\n"
            
            buffer = ""
            current_agent = "Orchestrator"
            token_buffer = ""
            MIN_TOKEN_LENGTH = 3  # Reduced for more granular streaming
            last_agent = None  # Track agent changes
            
            async for chunk in orchestrator.stream(
                message=request.message,
                conversation_id=conversation_id,
                user_id=request.user_id,
                context=request.context,
                thread_id=thread_id
            ):
                if chunk["type"] == "token":
                    # Handle content that might be a list or string
                    content = chunk["content"]
                    if isinstance(content, list):
                        content = "".join(str(c) for c in content)
                    else:
                        content = str(content)
                    
                    # Check if agent changed - if so, reset buffer
                    new_agent = chunk.get("agent", current_agent)
                    if new_agent != current_agent:
                        # Clear buffer when agent changes
                        buffer = ""
                        token_buffer = ""
                        current_agent = new_agent
                    
                    buffer += content
                    token_buffer += content
                    
                    # Send updates in larger chunks for smoother display
                    if len(token_buffer) >= MIN_TOKEN_LENGTH or content.endswith(('.', '!', '?', '\n')):
                        yield json.dumps({
                            "event": "agent_message",
                            "agent": current_agent,
                            "message": buffer,  # Keep full message for backward compatibility
                            "tokens": [token_buffer]  # Send only the new tokens
                        }) + "\n"
                        token_buffer = ""  # Reset token buffer after sending
                
                elif chunk["type"] == "agent_complete":
                    # Flush any remaining tokens
                    if token_buffer:
                        yield json.dumps({
                            "event": "agent_message",
                            "agent": current_agent,
                            "message": buffer,
                            "tokens": [token_buffer]
                        }) + "\n"
                        token_buffer = ""
                    
                    if buffer:
                        yield json.dumps({
                            "event": "agent_complete",
                            "agent": chunk["agent"],
                            "message": buffer
                        }) + "\n"
                    buffer = ""
                
                elif chunk["type"] == "error":
                    yield json.dumps({
                        "event": "error",
                        "error": chunk["error"]
                    }) + "\n"
                    break
                
                elif chunk["type"] == "complete":
                    # Stream has completed successfully
                    logger.info("Stream completed from orchestrator")
                    break
            
            # Flush any remaining tokens before completion
            if token_buffer:
                yield json.dumps({
                    "event": "agent_message",
                    "agent": current_agent,
                    "message": buffer,
                    "tokens": [token_buffer]
                }) + "\n"
            
            # Send final completion message
            if buffer:
                yield json.dumps({
                    "event": "agent_complete",
                    "agent": current_agent,
                    "message": buffer
                }) + "\n"
            
            # Send done event
            yield json.dumps({
                "event": "done",
                "message": "Completed"
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Error in HTTP stream: {e}")
            yield json.dumps({
                "event": "error",
                "error": str(e)
            }) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "close"
        }
    )

@router.post("/run")
async def chat_run(request: ChatRequest):
    """Compatibility endpoint for existing frontend - uses HTTP streaming"""
    return await chat_stream(request)

@router.post("/message")
async def chat_message(request: ChatRequest):
    """Standard POST endpoint for non-streaming chat"""
    
    orchestrator = get_orchestrator()
    
    try:
        result = await orchestrator.run(
            message=request.message,
            conversation_id=request.conversation_id,
            user_id=request.user_id,
            context=request.context,
            thread_id=request.thread_id
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))
        
        messages = []
        for msg in result["messages"]:
            messages.append({
                "role": "user" if msg.__class__.__name__ == "HumanMessage" else "assistant",
                "content": msg.content,
                "metadata": getattr(msg, "metadata", {})
            })
        
        return {
            "success": True,
            "messages": messages,
            "last_agent": result.get("last_agent"),
            "metadata": result.get("metadata", {})
        }
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents")
async def list_agents():
    """List available agents"""
    
    orchestrator = get_orchestrator()
    
    agents = []
    for name, agent in orchestrator.agents.items():
        agents.append({
            "name": name,
            "description": agent.description
        })
    
    return {"agents": agents}