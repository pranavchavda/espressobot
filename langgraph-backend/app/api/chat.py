"""
Chat API using Progressive Orchestrator
Implements: User → Orchestrator → Agent1 → Orchestrator → Agent2 → Orchestrator → User
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

from app.orchestrator import get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatMessage(BaseModel):
    message: str
    thread_id: Optional[str] = None
    conversation_id: Optional[str] = None  # Also accept conversation_id
    conv_id: Optional[str] = None  # Frontend uses conv_id
    user_id: Optional[str] = "1"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    agent: str = "orchestrator"

@router.post("/message")
async def send_message(chat_message: ChatMessage) -> ChatResponse:
    """
    Process a chat message using the progressive orchestrator
    """
    try:
        # Use thread_id, conversation_id, or conv_id - generate if none provided  
        thread_id = chat_message.thread_id or chat_message.conversation_id or chat_message.conv_id
        if not thread_id:
            thread_id = f"chat-{uuid.uuid4()}"
            logger.warning(f"No thread_id or conversation_id provided, generated new one: {thread_id}")
        else:
            logger.info(f"Using thread_id: {thread_id}")
        
        # Get the orchestrator
        orchestrator = await get_orchestrator()
        
        # Process the message progressively
        response_parts = []
        async for token in orchestrator.orchestrate(
            message=chat_message.message,
            thread_id=thread_id,
            user_id=chat_message.user_id
        ):
            response_parts.append(token)
        
        full_response = "".join(response_parts)
        
        return ChatResponse(
            response=full_response,
            conversation_id=thread_id,
            agent="orchestrator"
        )
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stream")
async def stream_message(chat_message: ChatMessage):
    """
    Stream a chat message response using the progressive orchestrator
    """
    # Use conv_id, thread_id, or conversation_id - frontend sends conv_id
    thread_id = chat_message.conv_id or chat_message.thread_id or chat_message.conversation_id
    if not thread_id:
        thread_id = f"chat-{int(time.time())}"
        logger.info(f"Generated new thread_id: {thread_id}")
    else:
        logger.info(f"Using thread_id: {thread_id}")
    
    async def generate() -> AsyncGenerator[str, None]:
        try:
            # Send conversation ID early
            yield json.dumps({
                "event": "conversation_id",
                "conv_id": thread_id,
                "thread_id": thread_id
            }) + "\n"
            
            # Initial UI message
            yield json.dumps({
                "event": "agent_message",
                "agent": "Orchestrator",
                "message": "Processing your request...",
                "tokens": []
            }) + "\n"
            
            # Get the orchestrator
            orchestrator = await get_orchestrator()
            
            # Collect all tokens for the response
            all_tokens = []
            
            # Process the message progressively
            async for token in orchestrator.orchestrate(
                message=chat_message.message,
                thread_id=thread_id,
                user_id=chat_message.user_id
            ):
                all_tokens.append(token)
                # Send token delta
                yield json.dumps({
                    "event": "token",
                    "token": token,
                    "tokens": all_tokens
                }) + "\n"
            
            # Send completion event
            yield json.dumps({
                "event": "completion",
                "message": "".join(all_tokens),
                "agent": "orchestrator"
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            yield json.dumps({
                "event": "error",
                "error": str(e)
            }) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )

@router.post("/sse")
async def sse_message(chat_message: ChatMessage):
    """
    SSE endpoint that emits well-formed Server-Sent Events for chat streaming.
    Events:
      - conversation_id: { conv_id, thread_id }
      - start: {}
      - agent_message: { agent, tokens: [token] }
      - agent_complete: { message, agent }
      - done: {}
      - error: { error }
    """
    # Determine thread id
    thread_id = chat_message.conv_id or chat_message.thread_id or chat_message.conversation_id
    if not thread_id:
        thread_id = f"chat-{int(time.time())}"
        logger.info(f"[SSE] Generated new thread_id: {thread_id}")
    else:
        logger.info(f"[SSE] Using thread_id: {thread_id}")

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            # Immediately send conversation id so client can bind UI state
            yield f"event: conversation_id\n" \
                  f"data: {json.dumps({'conv_id': thread_id, 'thread_id': thread_id})}\n\n"

            # Optional start signal
            yield "event: start\ndata: {}\n\n"

            orchestrator = await get_orchestrator()

            all_tokens = []

            # Stream token-by-token as agent_message events with tokens array
            async for token in orchestrator.orchestrate(
                message=chat_message.message,
                thread_id=thread_id,
                user_id=chat_message.user_id
            ):
                all_tokens.append(token)
                payload = {"agent": "orchestrator", "tokens": [token]}
                yield f"event: agent_message\ndata: {json.dumps(payload)}\n\n"

            final_message = "".join(all_tokens)

            # Signal completion with final message
            yield f"event: agent_complete\ndata: {json.dumps({'message': final_message, 'agent': 'orchestrator'})}\n\n"

            # Final done event
            yield "event: done\ndata: {}\n\n"

        except Exception as e:
            logger.error(f"[SSE] Error in streaming: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "orchestrator": "progressive"}