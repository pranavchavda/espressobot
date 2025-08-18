"""
Scratchpad API Endpoints

FastAPI router providing scratchpad functionality:
- Read/write persistent note content
- Add timestamped entries  
- Clear all content
- Export functionality

The scratchpad provides a shared note-taking space for users across all agent conversations.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from datetime import datetime
import logging
import json
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response models
class ScratchpadAction(BaseModel):
    action: str  # read, write, add_entry, clear
    content: Optional[str] = None
    author: Optional[str] = "User"

# In-memory storage for now (can be moved to database later)
scratchpad_data = {
    "content": "",
    "entries": [],
    "last_updated": None
}

@router.post("/scratchpad")
async def handle_scratchpad_action(
    request: ScratchpadAction,
    db: AsyncSession = Depends(get_db)
):
    """Handle scratchpad actions"""
    try:
        global scratchpad_data
        
        if request.action == "read":
            return {
                "success": True,
                "data": scratchpad_data
            }
        
        elif request.action == "write":
            scratchpad_data["content"] = request.content or ""
            scratchpad_data["last_updated"] = datetime.utcnow().isoformat()
            
            return {
                "success": True,
                "data": scratchpad_data,
                "message": "Content saved successfully"
            }
        
        elif request.action == "add_entry":
            if not request.content or not request.content.strip():
                raise HTTPException(status_code=400, detail="Entry content cannot be empty")
            
            entry = {
                "id": str(uuid.uuid4()),
                "content": request.content.strip(),
                "author": request.author or "User",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            scratchpad_data["entries"].append(entry)
            scratchpad_data["last_updated"] = datetime.utcnow().isoformat()
            
            return {
                "success": True,
                "data": scratchpad_data,
                "message": "Entry added successfully"
            }
        
        elif request.action == "clear":
            scratchpad_data["content"] = ""
            scratchpad_data["entries"] = []
            scratchpad_data["last_updated"] = datetime.utcnow().isoformat()
            
            return {
                "success": True,
                "data": scratchpad_data,
                "message": "Scratchpad cleared successfully"
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling scratchpad action {request.action}: {e}")
        raise HTTPException(status_code=500, detail="Failed to handle scratchpad action")

@router.get("/scratchpad")
async def get_scratchpad_data(
    db: AsyncSession = Depends(get_db)
):
    """Get current scratchpad data (alternative GET endpoint)"""
    try:
        global scratchpad_data
        return {
            "success": True,
            "data": scratchpad_data
        }
    except Exception as e:
        logger.error(f"Error fetching scratchpad data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scratchpad data")

@router.delete("/scratchpad")
async def clear_scratchpad(
    db: AsyncSession = Depends(get_db)
):
    """Clear all scratchpad data"""
    try:
        global scratchpad_data
        scratchpad_data["content"] = ""
        scratchpad_data["entries"] = []
        scratchpad_data["last_updated"] = datetime.utcnow().isoformat()
        
        return {
            "success": True,
            "data": scratchpad_data,
            "message": "Scratchpad cleared successfully"
        }
    except Exception as e:
        logger.error(f"Error clearing scratchpad: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear scratchpad")

@router.post("/scratchpad/export")
async def export_scratchpad(
    format: str = "json",
    db: AsyncSession = Depends(get_db)
):
    """Export scratchpad data"""
    try:
        global scratchpad_data
        
        if format == "json":
            return {
                "success": True,
                "data": scratchpad_data,
                "export_format": "json"
            }
        elif format == "text":
            # Convert to plain text format
            text_content = f"# Scratchpad Export\n\n"
            text_content += f"Last Updated: {scratchpad_data.get('last_updated', 'Unknown')}\n\n"
            
            if scratchpad_data.get('content'):
                text_content += f"## Main Content\n\n{scratchpad_data['content']}\n\n"
            
            if scratchpad_data.get('entries'):
                text_content += f"## Entries ({len(scratchpad_data['entries'])})\n\n"
                for i, entry in enumerate(reversed(scratchpad_data['entries']), 1):
                    text_content += f"### Entry {i}\n"
                    text_content += f"Author: {entry.get('author', 'Unknown')}\n"
                    text_content += f"Date: {entry.get('timestamp', 'Unknown')}\n"
                    text_content += f"Content: {entry.get('content', '')}\n\n"
            
            return {
                "success": True,
                "data": text_content,
                "export_format": "text"
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {format}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting scratchpad: {e}")
        raise HTTPException(status_code=500, detail="Failed to export scratchpad data")