"""
Authentication Proxy API for bridging Google OAuth tokens between frontend and backend.
Provides secure token caching with TTL and fallback mechanisms.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
import redis.asyncio as redis
import json
import logging
from datetime import datetime, timedelta
import os
import asyncpg
from app.db.connection_pool import get_database_pool

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# Redis connection for token caching
redis_client: Optional[redis.Redis] = None

class TokenData(BaseModel):
    """Token data structure for OAuth tokens"""
    access_token: str = Field(..., description="Google OAuth access token")
    refresh_token: Optional[str] = Field(None, description="Google OAuth refresh token")
    token_expiry: Optional[datetime] = Field(None, description="Token expiration time")
    scopes: Optional[list[str]] = Field(default=[], description="Token scopes")
    
class AuthProxyRequest(BaseModel):
    """Request model for storing auth tokens"""
    user_id: int = Field(..., description="User ID")
    tokens: TokenData = Field(..., description="OAuth token data")
    ttl_seconds: Optional[int] = Field(default=3600, description="Cache TTL in seconds")

class AuthProxyResponse(BaseModel):
    """Response model for auth proxy operations"""
    success: bool
    message: str
    cache_key: Optional[str] = None
    expires_at: Optional[datetime] = None

async def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for token caching"""
    global redis_client
    
    if redis_client is None:
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
            redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            await redis_client.ping()
            logger.info("Redis client connected successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Auth proxy will use database fallback only.")
            redis_client = None
    
    return redis_client

async def store_tokens_in_cache(user_id: int, tokens: TokenData, ttl: int = 3600) -> Optional[str]:
    """Store tokens in Redis cache with TTL"""
    redis_conn = await get_redis_client()
    if not redis_conn:
        return None
    
    cache_key = f"auth_tokens:{user_id}"
    token_data = {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_expiry": tokens.token_expiry.isoformat() if tokens.token_expiry else None,
        "scopes": tokens.scopes,
        "cached_at": datetime.utcnow().isoformat()
    }
    
    try:
        await redis_conn.setex(
            cache_key,
            ttl,
            json.dumps(token_data, default=str)
        )
        logger.info(f"Stored auth tokens in cache for user {user_id} with TTL {ttl}s")
        return cache_key
    except Exception as e:
        logger.error(f"Failed to cache tokens for user {user_id}: {e}")
        return None

async def get_tokens_from_cache(user_id: int) -> Optional[TokenData]:
    """Retrieve tokens from Redis cache"""
    redis_conn = await get_redis_client()
    if not redis_conn:
        return None
    
    cache_key = f"auth_tokens:{user_id}"
    
    try:
        cached_data = await redis_conn.get(cache_key)
        if not cached_data:
            return None
        
        token_data = json.loads(cached_data)
        return TokenData(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expiry=datetime.fromisoformat(token_data["token_expiry"]) if token_data.get("token_expiry") else None,
            scopes=token_data.get("scopes", [])
        )
    except Exception as e:
        logger.error(f"Failed to retrieve cached tokens for user {user_id}: {e}")
        return None

@router.post("/store-tokens", response_model=AuthProxyResponse)
async def store_tokens(
    request: AuthProxyRequest
) -> AuthProxyResponse:
    """
    Store Google OAuth tokens for a user with secure caching.
    Tokens are stored in Redis with TTL and also persisted to database.
    """
    try:
        # Get database connection
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://").replace("+asyncpg://", "://")
        
        db_pool = get_database_pool()
        async with db_pool.acquire() as conn:
            # Validate user exists
            user = await conn.fetchrow(
                "SELECT id, email FROM users WHERE id = $1",
                request.user_id
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {request.user_id} not found"
                )
            
            # Update user's tokens in database (persistent storage)
            await conn.execute(
                """
                UPDATE users 
                SET google_access_token = $1, 
                    google_refresh_token = $2, 
                    google_token_expiry = $3
                WHERE id = $4
                """,
                request.tokens.access_token,
                request.tokens.refresh_token,
                request.tokens.token_expiry,
                request.user_id
            )
            logger.info(f"Updated database tokens for user {request.user_id}")
        
        # Store in Redis cache for fast access
        cache_key = await store_tokens_in_cache(
            request.user_id, 
            request.tokens, 
            request.ttl_seconds
        )
        
        expires_at = datetime.utcnow() + timedelta(seconds=request.ttl_seconds)
        
        return AuthProxyResponse(
            success=True,
            message=f"Tokens stored successfully for user {request.user_id}",
            cache_key=cache_key,
            expires_at=expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store tokens for user {request.user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store tokens: {str(e)}"
        )

@router.get("/get-tokens/{user_id}", response_model=Dict[str, Any])
async def get_tokens(
    user_id: int
) -> Dict[str, Any]:
    """
    Retrieve Google OAuth tokens for a user.
    First checks Redis cache, then falls back to database.
    """
    try:
        # First try Redis cache
        cached_tokens = await get_tokens_from_cache(user_id)
        if cached_tokens:
            logger.info(f"Retrieved tokens from cache for user {user_id}")
            return {
                "success": True,
                "source": "cache",
                "tokens": {
                    "access_token": cached_tokens.access_token,
                    "refresh_token": cached_tokens.refresh_token,
                    "token_expiry": cached_tokens.token_expiry.isoformat() if cached_tokens.token_expiry else None,
                    "scopes": cached_tokens.scopes
                }
            }
        
        # Fallback to database
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://").replace("+asyncpg://", "://")
        
        db_pool = get_database_pool()
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow(
                "SELECT google_access_token, google_refresh_token, google_token_expiry FROM users WHERE id = $1",
                user_id
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {user_id} not found"
                )
            
            if not user['google_access_token']:
                return {
                    "success": False,
                    "message": "No Google OAuth tokens found for user",
                    "source": "database"
                }
            
            logger.info(f"Retrieved tokens from database for user {user_id}")
            return {
                "success": True,
                "source": "database",
                "tokens": {
                    "access_token": user['google_access_token'],
                    "refresh_token": user['google_refresh_token'],
                    "token_expiry": user['google_token_expiry'].isoformat() if user['google_token_expiry'] else None,
                    "scopes": []  # Scopes not stored in current database schema
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve tokens for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve tokens: {str(e)}"
        )

@router.delete("/revoke-tokens/{user_id}", response_model=AuthProxyResponse)
async def revoke_tokens(
    user_id: int
) -> AuthProxyResponse:
    """
    Revoke and clear Google OAuth tokens for a user.
    Removes from both cache and database.
    """
    try:
        # Clear from Redis cache
        redis_conn = await get_redis_client()
        if redis_conn:
            cache_key = f"auth_tokens:{user_id}"
            await redis_conn.delete(cache_key)
            logger.info(f"Cleared cached tokens for user {user_id}")
        
        # Clear from database
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://").replace("+asyncpg://", "://")
        
        db_pool = get_database_pool()
        async with db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users 
                SET google_access_token = NULL, 
                    google_refresh_token = NULL, 
                    google_token_expiry = NULL
                WHERE id = $1
                """,
                user_id
            )
            logger.info(f"Cleared database tokens for user {user_id}")
        
        return AuthProxyResponse(
            success=True,
            message=f"Tokens revoked successfully for user {user_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to revoke tokens for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke tokens: {str(e)}"
        )

@router.get("/health")
async def auth_proxy_health() -> Dict[str, Any]:
    """Health check endpoint for auth proxy"""
    redis_conn = await get_redis_client()
    redis_status = "connected" if redis_conn else "unavailable"
    
    if redis_conn:
        try:
            await redis_conn.ping()
            redis_status = "healthy"
        except Exception:
            redis_status = "error"
    
    return {
        "status": "healthy",
        "redis_cache": redis_status,
        "database_fallback": "available",
        "timestamp": datetime.utcnow().isoformat()
    }
