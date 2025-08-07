from fastapi import APIRouter, HTTPException, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import os
import logging
import asyncpg
import json

router = APIRouter()
logger = logging.getLogger(__name__)

# Get database URL for direct connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

async def get_db_connection():
    """Get direct asyncpg connection to PostgreSQL"""
    return await asyncpg.connect(DATABASE_URL)

class ConversationResponse(BaseModel):
    id: str  # Thread ID as string
    title: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    message_count: int

class UpdateTitleRequest(BaseModel):
    title: str
    auto_generated: Optional[bool] = False

@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    user_id: Optional[str] = Header(None, alias="User-ID")
):
    """List all conversations (thread IDs) from LangGraph checkpoints"""
    try:
        conn = await get_db_connection()
        try:
            # Create metadata table if it doesn't exist
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_metadata (
                    thread_id TEXT PRIMARY KEY,
                    title TEXT,
                    auto_generated BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Query distinct thread_ids from checkpoints table with titles
            rows = await conn.fetch("""
                SELECT 
                    c.thread_id,
                    COUNT(*) as message_count,
                    m.title,
                    m.created_at,
                    m.updated_at
                FROM checkpoints c
                LEFT JOIN conversation_metadata m ON c.thread_id = m.thread_id
                WHERE c.thread_id IS NOT NULL
                GROUP BY c.thread_id, m.title, m.created_at, m.updated_at
                ORDER BY COALESCE(m.updated_at, m.created_at, CURRENT_TIMESTAMP) DESC
                LIMIT 50
            """)
            
            response = []
            for row in rows:
                thread_id = row['thread_id']
                
                # Use stored title or generate a default
                if row['title']:
                    title = row['title']
                else:
                    # Default title with emoji
                    title = f"💬 Chat {thread_id[:8]}..." if len(thread_id) > 8 else f"💬 Chat {thread_id}"
                
                # Use stored timestamps or current time as fallback
                from datetime import datetime
                created_at = row['created_at'] if row['created_at'] else datetime.utcnow()
                updated_at = row['updated_at'] if row['updated_at'] else created_at
                
                response.append(ConversationResponse(
                    id=thread_id,
                    title=title,
                    created_at=created_at,
                    updated_at=updated_at,
                    message_count=row['message_count']
                ))
            
            logger.info(f"Found {len(response)} conversations")
            return response
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return []

@router.delete("/{thread_id}")
async def delete_conversation(
    thread_id: str,
    user_id: Optional[str] = Header(None, alias="User-ID")
):
    """Delete a conversation from LangGraph checkpoints"""
    try:
        conn = await get_db_connection()
        try:
            # Delete all checkpoints for this thread
            result = await conn.execute("""
                DELETE FROM checkpoints 
                WHERE thread_id = $1
            """, thread_id)
            
            # Check if any rows were deleted
            if result.split()[-1] == '0':
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            logger.info(f"Deleted conversation {thread_id}")
            return {"success": True, "message": "Conversation deleted"}
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting conversation {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.get("/{thread_id}")
async def get_conversation(
    thread_id: str,
    user_id: Optional[str] = Header(None, alias="User-ID")
):
    """Get a specific conversation with messages from LangGraph checkpoints"""
    try:
        # Get the orchestrator with properly initialized checkpointer
        from app.api.chat import get_orchestrator
        orchestrator = get_orchestrator()
        
        # Create config for this thread
        config = {"configurable": {"thread_id": thread_id}}
        
        # Get the latest checkpoint with deserialized messages
        checkpoint = orchestrator.checkpointer.get(config)
        
        if not checkpoint:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = []
        
        # Extract messages from checkpoint - it's a dictionary, not an object
        channel_values = checkpoint.get("channel_values", {})
        if 'messages' in channel_values:
            msg_list = channel_values['messages']
            
            for msg in msg_list:
                if hasattr(msg, 'content'):
                    content = msg.content
                    class_name = str(type(msg).__name__).lower()
                    role = "user" if 'human' in class_name else "assistant"
                    
                    messages.append({
                        "id": f"msg-{len(messages)}",
                        "role": role,
                        "content": content,
                        "created_at": datetime.utcnow().isoformat()
                    })
        
        # Use current time as placeholder since LangGraph doesn't store timestamps
        now = datetime.utcnow()
        title = f"Chat {thread_id[:8]}..." if len(thread_id) > 8 else f"Chat {thread_id}"
        
        return {
            "id": thread_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
            "messages": messages,
            "tasks": [],
            "taskMarkdown": None,
            "topic_title": title,
            "topic_details": None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting conversation {thread_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{thread_id}/title")
async def update_conversation_title(
    thread_id: str,
    request: UpdateTitleRequest,
    user_id: Optional[str] = Header(None, alias="User-ID")
):
    """Update the title of a conversation"""
    try:
        # Store title in a separate metadata table or as part of checkpoint metadata
        # For now, we'll store it in the checkpoint metadata
        conn = await get_db_connection()
        try:
            # Check if we have a metadata table, if not create it
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_metadata (
                    thread_id TEXT PRIMARY KEY,
                    title TEXT,
                    auto_generated BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Upsert the title
            await conn.execute("""
                INSERT INTO conversation_metadata (thread_id, title, auto_generated, updated_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                ON CONFLICT (thread_id) 
                DO UPDATE SET 
                    title = EXCLUDED.title,
                    auto_generated = EXCLUDED.auto_generated,
                    updated_at = CURRENT_TIMESTAMP
            """, thread_id, request.title, request.auto_generated)
            
            logger.info(f"Updated title for conversation {thread_id}: {request.title}")
            return {"success": True, "title": request.title}
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error updating title for {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update title: {str(e)}")

@router.post("/{thread_id}/generate-title")
async def generate_conversation_title(
    thread_id: str,
    user_id: Optional[str] = Header(None, alias="User-ID")
):
    """Generate a title for a conversation based on first message"""
    try:
        # Get the first message from the conversation
        from app.api.chat import get_orchestrator
        orchestrator = get_orchestrator()
        
        config = {"configurable": {"thread_id": thread_id}}
        checkpoint = orchestrator.checkpointer.get(config)
        
        if not checkpoint:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Extract first user message
        channel_values = checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])
        
        first_user_message = None
        for msg in messages:
            if hasattr(msg, '__class__') and 'Human' in msg.__class__.__name__:
                first_user_message = msg.content
                break
        
        if not first_user_message:
            return {"title": "💬 New Conversation"}
        
        # Generate title
        from app.api.title_generator import get_title_generator
        generator = get_title_generator()
        title = await generator.generate_title(first_user_message)
        
        # Store the generated title
        await update_conversation_title(
            thread_id=thread_id,
            request=UpdateTitleRequest(title=title, auto_generated=True),
            user_id=user_id
        )
        
        return {"title": title, "auto_generated": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating title for {thread_id}: {e}")
        return {"title": "💬 New Conversation", "error": str(e)}