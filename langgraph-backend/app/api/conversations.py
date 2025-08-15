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
            
            # Query conversations from both checkpoints and conversation_metadata
            # This ensures we show conversations from both LangGraph and Progressive orchestrators
            rows = await conn.fetch("""
                WITH all_conversations AS (
                    -- Get conversations from checkpoints (LangGraph)
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
                    
                    UNION
                    
                    -- Get conversations only in metadata (Progressive orchestrator)
                    SELECT 
                        m.thread_id,
                        0 as message_count,  -- No checkpoint messages
                        m.title,
                        m.created_at,
                        m.updated_at
                    FROM conversation_metadata m
                    WHERE NOT EXISTS (
                        SELECT 1 FROM checkpoints c WHERE c.thread_id = m.thread_id
                    )
                )
                SELECT * FROM all_conversations
                ORDER BY COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) DESC
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
            checkpoint_result = await conn.execute("""
                DELETE FROM checkpoints 
                WHERE thread_id = $1
            """, thread_id)
            
            # Also delete from conversation_metadata
            metadata_result = await conn.execute("""
                DELETE FROM conversation_metadata 
                WHERE thread_id = $1
            """, thread_id)
            
            # Also delete from progressive_messages if table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'progressive_messages'
                )
            """)
            
            if table_exists:
                await conn.execute("""
                    DELETE FROM progressive_messages 
                    WHERE thread_id = $1
                """, thread_id)
            
            # Check if any rows were deleted from either table
            checkpoint_deleted = checkpoint_result.split()[-1] != '0'
            metadata_deleted = metadata_result.split()[-1] != '0'
            
            if not checkpoint_deleted and not metadata_deleted:
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
    """Get a specific conversation with messages"""
    try:
        conn = await get_db_connection()
        try:
            # First check if this is a Progressive orchestrator conversation (only in metadata)
            metadata = await conn.fetchrow("""
                SELECT title, created_at, updated_at
                FROM conversation_metadata
                WHERE thread_id = $1
            """, thread_id)
            
            if metadata and not await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM checkpoints WHERE thread_id = $1 LIMIT 1)
            """, thread_id):
                # This is a Progressive orchestrator conversation without checkpoints
                # Load messages from progressive_messages table
                messages = []
                
                # Check if progressive_messages table exists and has messages
                table_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'progressive_messages'
                    )
                """)
                
                if table_exists:
                    rows = await conn.fetch("""
                        SELECT role, content, created_at 
                        FROM progressive_messages 
                        WHERE thread_id = $1
                        ORDER BY created_at ASC
                    """, thread_id)
                    
                    for idx, row in enumerate(rows):
                        messages.append({
                            "id": f"msg-{idx}",
                            "role": row['role'],
                            "content": row['content'],
                            "created_at": row['created_at'].isoformat() if row['created_at'] else datetime.utcnow().isoformat()
                        })
                
                # If no messages found, return a helpful message
                if not messages:
                    messages = [
                        {
                            "id": "msg-0",
                            "role": "system",
                            "content": f"This conversation '{metadata['title']}' was created on {metadata['created_at'].strftime('%Y-%m-%d %H:%M')}.",
                            "created_at": metadata['created_at'].isoformat()
                        }
                    ]
                
                return {
                    "id": thread_id,
                    "thread_id": thread_id,
                    "title": metadata['title'],
                    "created_at": metadata['created_at'],
                    "updated_at": metadata['updated_at'],
                    "messages": messages,
                    "tasks": [],
                    "taskMarkdown": None,
                    "topic_title": metadata['title'],
                    "topic_details": None,
                    "currentTasks": []  # Frontend expects this field
                }
            
            # Check if this thread exists in checkpoints (old LangGraph)
            has_checkpoint = await conn.fetchval("""
                SELECT EXISTS(
                    SELECT 1 FROM checkpoints 
                    WHERE thread_id = $1
                    LIMIT 1
                )
            """, thread_id)
            
            if has_checkpoint:
                # Load messages directly from checkpoint in database
                try:
                    # Get the latest checkpoint (not the init one)
                    checkpoint_row = await conn.fetchrow("""
                        SELECT checkpoint, metadata
                        FROM checkpoints 
                        WHERE thread_id = $1 
                        AND checkpoint_id != 'init'
                        ORDER BY checkpoint_id DESC
                        LIMIT 1
                    """, thread_id)
                    
                    # If no messages checkpoint, try the init checkpoint
                    if not checkpoint_row:
                        checkpoint_row = await conn.fetchrow("""
                            SELECT checkpoint, metadata
                            FROM checkpoints 
                            WHERE thread_id = $1 
                            AND checkpoint_id = 'init'
                            LIMIT 1
                        """, thread_id)
                    
                    if checkpoint_row:
                        messages = []
                        checkpoint_data = json.loads(checkpoint_row['checkpoint'])
                        
                        # Extract messages from checkpoint
                        channel_values = checkpoint_data.get("channel_values", {})
                        if 'messages' in channel_values:
                            msg_list = channel_values['messages']
                            
                            for msg in msg_list:
                                # Handle both dict format (from custom orchestrator) 
                                # and object format (from old LangGraph)
                                if isinstance(msg, dict):
                                    content = msg.get('content', '')
                                    role = "user" if msg.get('type') == 'human' else "assistant"
                                else:
                                    # Old format with objects
                                    if hasattr(msg, 'content'):
                                        content = msg.content
                                        class_name = str(type(msg).__name__).lower()
                                        role = "user" if 'human' in class_name else "assistant"
                                    else:
                                        continue
                                
                                messages.append({
                                    "id": f"msg-{len(messages)}",
                                    "role": role,
                                    "content": content,
                                    "created_at": datetime.utcnow().isoformat()
                                })
                        
                        # Get title from metadata if exists
                        title_row = await conn.fetchrow("""
                            SELECT title, created_at, updated_at 
                            FROM conversation_metadata 
                            WHERE thread_id = $1
                        """, thread_id)
                        
                        if title_row and title_row['title']:
                            title = title_row['title']
                            created_at = title_row['created_at'] or datetime.utcnow()
                            updated_at = title_row['updated_at'] or created_at
                        else:
                            title = f"Chat {thread_id[:8]}..." if len(thread_id) > 8 else f"Chat {thread_id}"
                            created_at = datetime.utcnow()
                            updated_at = created_at
                        
                        return {
                            "id": thread_id,
                            "title": title,
                            "created_at": created_at,
                            "updated_at": updated_at,
                            "messages": messages,
                            "tasks": [],
                            "taskMarkdown": None,
                            "topic_title": title,
                            "topic_details": None,
                            "currentTasks": []  # Frontend expects this field
                        }
                    
                except Exception as e:
                    logger.warning(f"Could not load conversation {thread_id}: {e}")
                
                # If we couldn't load the conversation, return a message
                return {
                    "id": thread_id,
                    "title": "Legacy Conversation",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "messages": [{
                        "id": "msg-0",
                        "role": "assistant",
                        "content": "This conversation could not be loaded. Please start a new conversation.",
                        "created_at": datetime.utcnow().isoformat()
                    }],
                    "tasks": [],
                    "taskMarkdown": None,
                    "topic_title": "Legacy Conversation",
                    "topic_details": None,
                    "currentTasks": []  # Frontend expects this field
                }
            
            # For new conversations (not in checkpoints), return empty structure
            # This allows the custom orchestrator to work without persistence
            return {
                "id": thread_id,
                "title": "New Conversation",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "messages": [],
                "tasks": [],
                "taskMarkdown": None,
                "topic_title": "New Conversation",
                "topic_details": None,
                "currentTasks": []
            }
            
        finally:
            await conn.close()
        
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