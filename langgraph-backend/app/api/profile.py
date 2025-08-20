"""
Profile API for user profile management
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import logging
import asyncpg
from app.db.connection_pool import get_database_connection

logger = logging.getLogger(__name__)

router = APIRouter()

class ProfileResponse(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    bio: Optional[str] = None

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None

@router.get("/profile")
async def get_profile(conn: asyncpg.Connection = Depends(get_database_connection)) -> ProfileResponse:
    """
    Get user profile - for now returns default user (id=1)
    TODO: Extract user from auth token when auth is fully implemented
    """
    try:
        # For now, get the default user (id=1)
        user = await conn.fetchrow("SELECT id, name, email, bio FROM users WHERE id = $1", 1)
        
        if not user:
            # Create default user if doesn't exist
            await conn.execute(
                """INSERT INTO users (id, name, email, bio, is_whitelisted, created_at) 
                   VALUES ($1, $2, $3, $4, $5, NOW())""",
                1, "Default User", "user@example.com", "", True
            )
            user = await conn.fetchrow("SELECT id, name, email, bio FROM users WHERE id = $1", 1)
        
        return ProfileResponse(
            name=user['name'],
            email=user['email'],
            bio=user['bio']
        )
        
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")

@router.put("/profile")
async def update_profile(
    profile_update: ProfileUpdate,
    conn: asyncpg.Connection = Depends(get_database_connection)
):
    """
    Update user profile - for now updates default user (id=1)
    TODO: Extract user from auth token when auth is fully implemented
    """
    try:
        # For now, update the default user (id=1)
        user = await conn.fetchrow("SELECT id FROM users WHERE id = $1", 1)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build update query dynamically based on provided fields
        updates = []
        values = []
        param_count = 1
        
        if profile_update.name is not None:
            updates.append(f"name = ${param_count}")
            values.append(profile_update.name)
            param_count += 1
            
        if profile_update.bio is not None:
            updates.append(f"bio = ${param_count}")
            values.append(profile_update.bio)
            param_count += 1
        
        if updates:
            # Add user_id at the end
            values.append(1)
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${param_count}"
            await conn.execute(query, *values)
        
        return {"message": "Profile updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")