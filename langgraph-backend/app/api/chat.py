from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
import json
import logging
import asyncio
import time
from app.orchestrator_direct import DirectOrchestrator
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)
router = APIRouter()

_orchestrator: Optional[DirectOrchestrator] = None

def get_orchestrator() -> DirectOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = DirectOrchestrator()
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
    
    # Get user_id from request - default to "1" if not provided
    user_id = request.user_id or "1"
    
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
            
            # Create message list for DirectOrchestrator
            messages = [HumanMessage(content=request.message)]
            
            async for chunk in orchestrator.stream(
                messages=messages,
                thread_id=thread_id,
                user_id=user_id
            ):
                # LangGraph returns chunks as {node_name: {state_updates}}
                logger.info(f"Stream chunk: {chunk}")
                
                # Extract messages from the chunk
                for node_name, state_updates in chunk.items():
                    if "messages" in state_updates:
                        # Get the last message (the new one)
                        messages_list = state_updates["messages"]
                        if messages_list and len(messages_list) > 0:
                            last_msg = messages_list[-1]
                            
                            # Check if it's an AI message
                            if hasattr(last_msg, 'content'):
                                content = last_msg.content
                                agent_name = last_msg.metadata.get("agent", node_name) if hasattr(last_msg, 'metadata') else node_name
                                
                                # Send the complete message
                                yield json.dumps({
                                    "event": "agent_message",
                                    "agent": agent_name,
                                    "message": content,
                                    "tokens": [content]
                                }) + "\n"
                
                # Skip the original handling since we're processing LangGraph chunks above
                continue
                
                # Original handling (disabled for now)
                if False and isinstance(chunk, dict) and chunk.get("type") == "token":
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
            
            # Auto-generate title if this is a new conversation (first message)
            try:
                # Check if conversation already has a title
                from app.api.conversations import get_db_connection
                conn = await get_db_connection()
                try:
                    # Ensure table exists
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS conversation_metadata (
                            thread_id TEXT PRIMARY KEY,
                            title TEXT,
                            auto_generated BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # Check if title exists for this thread
                    existing_title = await conn.fetchval("""
                        SELECT title FROM conversation_metadata 
                        WHERE thread_id = $1
                    """, thread_id)
                    
                    if not existing_title:
                        # This is a new conversation, generate title
                        from app.api.title_generator import get_title_generator
                        generator = get_title_generator()
                        title = await generator.generate_title(request.message)
                        
                        # Store the generated title
                        await conn.execute("""
                            INSERT INTO conversation_metadata (thread_id, title, auto_generated, updated_at)
                            VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP)
                            ON CONFLICT (thread_id) 
                            DO UPDATE SET 
                                title = EXCLUDED.title,
                                auto_generated = EXCLUDED.auto_generated,
                                updated_at = CURRENT_TIMESTAMP
                        """, thread_id, title)
                        
                        logger.info(f"Auto-generated title for new conversation {thread_id}: {title}")
                        
                        # Send title update event to frontend
                        yield json.dumps({
                            "event": "title_generated",
                            "thread_id": thread_id,
                            "title": title
                        }) + "\n"
                        
                finally:
                    await conn.close()
                    
            except Exception as e:
                logger.warning(f"Failed to auto-generate title for {thread_id}: {e}")
                # Don't fail the whole request if title generation fails
            
            # Send done event
            yield json.dumps({
                "event": "done",
                "message": "Completed"
            }) + "\n"
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error in HTTP stream: {e}\n{error_details}")
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
        
        # Auto-generate title if this is a new conversation
        generated_title = None
        try:
            thread_id = request.thread_id or request.conversation_id or f"chat-{int(time.time())}"
            from app.api.conversations import get_db_connection
            conn = await get_db_connection()
            try:
                # Ensure table exists
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_metadata (
                        thread_id TEXT PRIMARY KEY,
                        title TEXT,
                        auto_generated BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Check if title exists for this thread
                existing_title = await conn.fetchval("""
                    SELECT title FROM conversation_metadata 
                    WHERE thread_id = $1
                """, thread_id)
                
                if not existing_title:
                    # This is a new conversation, generate title
                    from app.api.title_generator import get_title_generator
                    generator = get_title_generator()
                    generated_title = await generator.generate_title(request.message)
                    
                    # Store the generated title
                    await conn.execute("""
                        INSERT INTO conversation_metadata (thread_id, title, auto_generated, updated_at)
                        VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP)
                        ON CONFLICT (thread_id) 
                        DO UPDATE SET 
                            title = EXCLUDED.title,
                            auto_generated = EXCLUDED.auto_generated,
                            updated_at = CURRENT_TIMESTAMP
                    """, thread_id, generated_title)
                    
                    logger.info(f"Auto-generated title for new conversation {thread_id}: {generated_title}")
                    
            finally:
                await conn.close()
                
        except Exception as e:
            logger.warning(f"Failed to auto-generate title: {e}")

        response_metadata = result.get("metadata", {})
        if generated_title:
            response_metadata["generated_title"] = generated_title

        return {
            "success": True,
            "messages": messages,
            "last_agent": result.get("last_agent"),
            "metadata": response_metadata
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