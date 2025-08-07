from fastapi import APIRouter, HTTPException, Header
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import os
import logging
import asyncpg

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

@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    user_id: Optional[str] = Header(None, alias="User-ID")
):
    """List all conversations (thread IDs) from LangGraph checkpoints"""
    try:
        conn = await get_db_connection()
        try:
            # Query distinct thread_ids from checkpoints table
            # LangGraph doesn't store timestamps, so we'll use a simple approach
            rows = await conn.fetch("""
                SELECT 
                    thread_id,
                    COUNT(*) as message_count
                FROM checkpoints 
                WHERE thread_id IS NOT NULL
                GROUP BY thread_id
                ORDER BY thread_id DESC
                LIMIT 50
            """)
            
            response = []
            for row in rows:
                thread_id = row['thread_id']
                # Generate a simple title from thread_id
                title = f"Chat {thread_id[:8]}..." if len(thread_id) > 8 else f"Chat {thread_id}"
                
                # Use current time as placeholder since LangGraph doesn't store timestamps
                from datetime import datetime
                now = datetime.utcnow()
                
                response.append(ConversationResponse(
                    id=thread_id,
                    title=title,
                    created_at=now,
                    updated_at=now,
                    message_count=row['message_count']
                ))
            
            logger.info(f"Found {len(response)} conversations")
            return response
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        return []

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

# Delete endpoint temporarily disabled - would need to implement checkpoint deletion
# @router.delete("/{thread_id}")
# async def delete_conversation(thread_id: str):
#     """Delete a conversation and its checkpoints"""
#     # TODO: Implement checkpoint deletion from LangGraph tables
#     pass