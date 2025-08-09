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

            # One outbound queue that interleaves graph chunks and token deltas
            out_q: asyncio.Queue = asyncio.Queue()
            stop_event = asyncio.Event()

            # Build message content with image support
            if request.image:
                # Multimodal message with image
                content = [
                    {"type": "text", "text": request.message}
                ]
                
                # Add image to content
                if request.image.get("type") == "url" or "url" in request.image:
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": request.image["url"]}
                    })
                elif request.image.get("type") == "data_url" or "data" in request.image:
                    # Handle data URL - it might already include the data:image prefix
                    data_url = request.image.get("data", request.image.get("dataUrl", ""))
                    if not data_url.startswith("data:"):
                        data_url = f"data:image/jpeg;base64,{data_url}"
                    content.append({
                        "type": "image_url", 
                        "image_url": {"url": data_url}
                    })
                elif "base64" in request.image:
                    content.append({
                        "type": "image_url", 
                        "image_url": {"url": f"data:image/jpeg;base64,{request.image['base64']}"}
                    })
                
                messages = [HumanMessage(content=content)]
                logger.info(f"Created multimodal message with image type: {request.image.get('type', 'unknown')}")
            else:
                # Text-only message
                messages = [HumanMessage(content=request.message)]

            async def produce_graph_chunks():
                try:
                    logger.info(f"Starting graph stream for thread {thread_id}")
                    chunk_count = 0
                    async for chunk in orchestrator.stream(messages=messages, thread_id=thread_id, user_id=user_id):
                        chunk_count += 1
                        logger.info(f"Received chunk {chunk_count} from orchestrator")
                        await out_q.put(("graph", chunk))
                    logger.info(f"Graph stream ended after {chunk_count} chunks")
                except Exception as e:
                    logger.error(f"Error in graph stream: {e}")
                    await out_q.put(("error", str(e)))
                finally:
                    logger.info("Sending graph_complete signal")
                    await out_q.put(("graph_complete", None))

            async def produce_token_deltas():
                try:
                    while not stop_event.is_set():
                        q = orchestrator.get_token_queue(thread_id)
                        if q is None:
                            await asyncio.sleep(0.005)
                            continue
                        try:
                            item = await asyncio.wait_for(q.get(), timeout=0.2)
                        except asyncio.TimeoutError:
                            continue
                        if isinstance(item, dict):
                            await out_q.put(("delta", item))
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    await out_q.put(("error", str(e)))

            task_graph = asyncio.create_task(produce_graph_chunks())
            task_tokens = asyncio.create_task(produce_token_deltas())

            graph_done = False
            any_delta_emitted = False
            try:
                while True:
                    kind, payload = await out_q.get()
                    if kind == "delta":
                        delta = payload.get("delta")
                        agent_for_delta = payload.get("agent") or "orchestrator"
                        if delta:
                            yield json.dumps({
                                "event": "assistant_delta",
                                "agent": agent_for_delta,
                                "conversation_id": thread_id,
                                "delta": delta
                            }) + "\n"
                            any_delta_emitted = True
                    elif kind == "graph":
                        chunk = payload
                        # Emit planner status and agent_complete when AIMessage lands
                        try:
                            for node_name, state_updates in chunk.items():
                                if isinstance(state_updates, dict) and state_updates.get("current_agent"):
                                    yield json.dumps({
                                        "event": "planner_status",
                                        "status": "routing",
                                        "agent": state_updates.get("current_agent")
                                    }) + "\n"
                                if "messages" in state_updates:
                                    msgs = state_updates["messages"]
                                    if msgs:
                                        last_msg = msgs[-1]
                                        try:
                                            from langchain_core.messages import AIMessage
                                            is_ai = isinstance(last_msg, AIMessage)
                                        except Exception:
                                            is_ai = hasattr(last_msg, 'type') and getattr(last_msg, 'type', '') == 'ai'
                                        if is_ai and hasattr(last_msg, 'content'):
                                            content = last_msg.content
                                            metadata = getattr(last_msg, 'metadata', {})
                                            agent_name = metadata.get("agent", node_name)
                                            is_direct_response = metadata.get("direct_response", False)
                                            
                                            if content:
                                                # Only synthesize deltas if:
                                                # 1. No real deltas were emitted AND
                                                # 2. This is not a direct orchestrator response (which already streamed)
                                                if not any_delta_emitted and not is_direct_response:
                                                    try:
                                                        step = 20
                                                        for i in range(0, len(content), step):
                                                            yield json.dumps({
                                                                "event": "assistant_delta",
                                                                "agent": agent_name or "orchestrator",
                                                                "conversation_id": thread_id,
                                                                "delta": content[i:i+step]
                                                            }) + "\n"
                                                    except Exception:
                                                        pass
                                                
                                                # Always send agent_complete for UI to know message is done
                                                yield json.dumps({
                                                    "event": "agent_complete",
                                                    "agent": agent_name,
                                                    "message": content
                                                }) + "\n"
                        except Exception:
                            pass
                    elif kind == "graph_complete":
                        logger.info("Received graph_complete signal, ending stream")
                        graph_done = True
                        stop_event.set()
                        break
                    elif kind == "error":
                        yield json.dumps({"event": "error", "error": payload}) + "\n"
                        graph_done = True
                        stop_event.set()
                        break

            finally:
                # Cancel token producer if still running
                if not task_tokens.done():
                    task_tokens.cancel()
                # Wait for graph task to finish
                try:
                    await task_graph
                except Exception:
                    pass

            # Drain any remaining token deltas
            try:
                q = orchestrator.get_token_queue(thread_id)
                if q is not None:
                    while True:
                        try:
                            item = q.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                        if isinstance(item, dict) and item.get("delta"):
                            yield json.dumps({
                                "event": "assistant_delta",
                                "agent": item.get("agent") or "orchestrator",
                                "conversation_id": thread_id,
                                "delta": item.get("delta")
                            }) + "\n"
            except Exception:
                pass

            # Optional: auto-generate a title for new conversations
            try:
                from app.api.conversations import get_db_connection
                conn = await get_db_connection()
                try:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS conversation_metadata (
                            thread_id TEXT PRIMARY KEY,
                            title TEXT,
                            auto_generated BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    existing_title = await conn.fetchval(
                        """
                        SELECT title FROM conversation_metadata 
                        WHERE thread_id = $1
                        """,
                        thread_id,
                    )
                    if not existing_title:
                        try:
                            from app.api.title_generator import get_title_generator
                            generator = get_title_generator()
                            # Add timeout to prevent hanging
                            title = await asyncio.wait_for(
                                generator.generate_title(request.message),
                                timeout=5.0
                            )
                            await conn.execute(
                                """
                                INSERT INTO conversation_metadata (thread_id, title, auto_generated, updated_at)
                                VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP)
                                ON CONFLICT (thread_id) 
                                DO UPDATE SET 
                                    title = EXCLUDED.title,
                                    auto_generated = EXCLUDED.auto_generated,
                                    updated_at = CURRENT_TIMESTAMP
                                """,
                                thread_id,
                                title,
                            )
                            yield json.dumps({
                                "event": "title_generated",
                                "thread_id": thread_id,
                                "title": title,
                            }) + "\n"
                        except asyncio.TimeoutError:
                            logger.warning(f"Title generation timed out for thread {thread_id}")
                        except Exception as e:
                            logger.warning(f"Title generation failed: {e}")
                finally:
                    await conn.close()
            except Exception as e:
                logger.warning(f"Title generation database error: {e}")
                pass

            # Signal done and cleanup
            logger.info(f"Sending done event for thread {thread_id}")
            yield json.dumps({"event": "done", "message": "Completed"}) + "\n"
            logger.info(f"Done event sent for thread {thread_id}")
            try:
                orchestrator.cleanup_token_queue(thread_id)
            except Exception:
                pass

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Error in HTTP stream: {e}\n{error_details}")
            yield json.dumps({"event": "error", "error": str(e)}) + "\n"
    
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