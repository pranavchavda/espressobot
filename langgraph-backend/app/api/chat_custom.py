"""
Chat API endpoint using the custom async orchestrator
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
import json
import logging
import asyncio
import time
from app.orchestrator_custom import get_orchestrator
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)
router = APIRouter()

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
    """Streaming endpoint for GUI compatibility using NDJSON format"""
    
    orchestrator = await get_orchestrator()
    
    # Use conv_id if provided (frontend compatibility)
    conversation_id = request.conv_id or request.conversation_id
    thread_id = request.thread_id or conversation_id or f"chat-{int(time.time())}"
    user_id = request.user_id or "1"
    
    async def generate():
        try:
            # Send conversation ID first - exactly as DirectOrchestrator does it
            yield json.dumps({
                "event": "conversation_id",
                "conv_id": thread_id,
                "thread_id": thread_id
            }) + "\n"
            
            # Send initial agent message
            yield json.dumps({
                "event": "agent_message",
                "agent": "Orchestrator",
                "message": "Processing your request...",
                "tokens": []
            }) + "\n"
            
            # Collect full response from orchestrator
            full_response = ""
            async for token in orchestrator.orchestrate(
                message=request.message,
                thread_id=thread_id,
                user_id=user_id
            ):
                full_response += token
            
            # Stream the response as assistant_delta events - matching DirectOrchestrator format
            chunk_size = 20
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i:i+chunk_size]
                yield json.dumps({
                    "event": "assistant_delta",
                    "agent": "orchestrator", 
                    "conversation_id": thread_id,
                    "delta": chunk
                }) + "\n"
                await asyncio.sleep(0.01)  # Small delay for smooth streaming effect
            
            # Don't send agent_complete for basic agent mode - it's not handled
            # The frontend will finalize the message when it receives the done event
            
            # Send done event to signal completion
            yield json.dumps({
                "event": "done",
                "message": "Completed"
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            yield json.dumps({
                "event": "error",
                "error": str(e)
            }) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",  # Back to NDJSON format
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/message")
async def chat_message(request: ChatRequest):
    """Non-streaming endpoint using custom orchestrator"""
    
    orchestrator = await get_orchestrator()
    
    conversation_id = request.conv_id or request.conversation_id
    thread_id = request.thread_id or conversation_id or f"chat-{int(time.time())}"
    user_id = request.user_id or "1"
    
    try:
        # Collect all tokens into a single response
        response = ""
        async for token in orchestrator.orchestrate(
            message=request.message,
            thread_id=thread_id,
            user_id=user_id
        ):
            response += token
        
        return {
            "response": response,
            "conversation_id": thread_id,
            "agent": "orchestrator"
        }
    
    except Exception as e:
        logger.error(f"Chat message error: {e}")
        raise HTTPException(status_code=500, detail=str(e))