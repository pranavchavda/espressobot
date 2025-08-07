"""
Authentication Helper for Google Workspace and GA4 agents.
Provides unified access to Google OAuth tokens with caching and fallback mechanisms.
"""
from typing import Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import logging
import os
import httpx
from datetime import datetime, timedelta
from app.database.session import AsyncSessionLocal
from app.database.models import User
from sqlalchemy import select

logger = logging.getLogger(__name__)

class GoogleAuthHelper:
    """
    Helper class for managing Google OAuth authentication across agents.
    Supports both cache-first and database-fallback patterns.
    """
    
    def __init__(self, user_id: int, required_scopes: Optional[list[str]] = None):
        self.user_id = user_id
        self.required_scopes = required_scopes or [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/tasks',
            'https://www.googleapis.com/auth/analytics.readonly'
        ]
        self.auth_proxy_base_url = os.getenv(
            "AUTH_PROXY_BASE_URL", 
            "http://localhost:8000/api/auth"
        )
        self._cached_credentials: Optional[Credentials] = None
        self._cache_expiry: Optional[datetime] = None
    
    async def get_credentials(self, force_refresh: bool = False) -> Optional[Credentials]:
        """
        Get Google OAuth credentials for the user.
        
        Args:
            force_refresh: Force refresh from database/auth proxy
            
        Returns:
            Google OAuth credentials or None if unavailable
        """
        try:
            # Check in-memory cache first (short-lived)
            if (
                not force_refresh and 
                self._cached_credentials and 
                self._cache_expiry and 
                datetime.utcnow() < self._cache_expiry and
                not self._cached_credentials.expired
            ):
                logger.debug(f"Using cached credentials for user {self.user_id}")
                return self._cached_credentials
            
            # Try auth proxy cache first
            credentials = await self._get_from_auth_proxy()
            if credentials:
                self._cache_credentials(credentials)
                return credentials
            
            # Fallback to direct database access
            credentials = await self._get_from_database()
            if credentials:
                # Store in auth proxy cache for next time
                await self._store_in_auth_proxy(credentials)
                self._cache_credentials(credentials)
                return credentials
            
            logger.warning(f"No Google credentials found for user {self.user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting credentials for user {self.user_id}: {e}")
            return None
    
    async def _get_from_auth_proxy(self) -> Optional[Credentials]:
        """
        Try to get credentials from the auth proxy cache.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.auth_proxy_base_url}/get-tokens/{self.user_id}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "tokens" in data:
                        token_data = data["tokens"]
                        
                        credentials = Credentials(
                            token=token_data["access_token"],
                            refresh_token=token_data.get("refresh_token"),
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=os.getenv("GOOGLE_CLIENT_ID"),
                            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                            scopes=self.required_scopes
                        )
                        
                        # Set expiry if provided
                        if token_data.get("token_expiry"):
                            credentials.expiry = datetime.fromisoformat(
                                token_data["token_expiry"]
                            )
                        
                        # Refresh if expired
                        if credentials.expired and credentials.refresh_token:
                            await self._refresh_credentials(credentials)
                        
                        logger.info(
                            f"Retrieved credentials from auth proxy cache for user {self.user_id} "
                            f"(source: {data.get('source', 'unknown')})"
                        )
                        return credentials
                        
        except Exception as e:
            logger.debug(f"Auth proxy unavailable for user {self.user_id}: {e}")
        
        return None
    
    async def _get_from_database(self) -> Optional[Credentials]:
        """
        Get credentials directly from database (fallback).
        """
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).where(User.id == self.user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.google_access_token:
                    return None
                
                credentials = Credentials(
                    token=user.google_access_token,
                    refresh_token=user.google_refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=os.getenv("GOOGLE_CLIENT_ID"),
                    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                    scopes=self.required_scopes
                )
                
                if user.google_token_expiry:
                    credentials.expiry = user.google_token_expiry
                
                # Refresh if expired
                if credentials.expired and credentials.refresh_token:
                    refreshed = await self._refresh_credentials(credentials)
                    if refreshed:
                        # Update database with new tokens
                        user.google_access_token = credentials.token
                        user.google_token_expiry = credentials.expiry
                        await session.commit()
                
                logger.info(f"Retrieved credentials from database for user {self.user_id}")
                return credentials
                
        except Exception as e:
            logger.error(f"Database credential retrieval failed for user {self.user_id}: {e}")
        
        return None
    
    async def _refresh_credentials(self, credentials: Credentials) -> bool:
        """
        Refresh expired OAuth credentials.
        
        Args:
            credentials: The credentials to refresh
            
        Returns:
            True if refresh was successful
        """
        try:
            logger.info(f"Refreshing expired credentials for user {self.user_id}")
            credentials.refresh(Request())
            logger.info(f"Successfully refreshed credentials for user {self.user_id}")
            return True
        except RefreshError as e:
            logger.error(f"Failed to refresh credentials for user {self.user_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error refreshing credentials for user {self.user_id}: {e}")
            return False
    
    async def _store_in_auth_proxy(self, credentials: Credentials) -> bool:
        """
        Store credentials in auth proxy cache.
        """
        try:
            token_data = {
                "user_id": self.user_id,
                "tokens": {
                    "access_token": credentials.token,
                    "refresh_token": credentials.refresh_token,
                    "token_expiry": credentials.expiry.isoformat() if credentials.expiry else None,
                    "scopes": list(credentials.scopes) if credentials.scopes else self.required_scopes
                },
                "ttl_seconds": 3600  # Cache for 1 hour
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.auth_proxy_base_url}/store-tokens",
                    json=token_data
                )
                
                if response.status_code == 200:
                    logger.info(f"Stored credentials in auth proxy cache for user {self.user_id}")
                    return True
                else:
                    logger.warning(
                        f"Failed to store credentials in auth proxy for user {self.user_id}: "
                        f"{response.status_code}"
                    )
                    
        except Exception as e:
            logger.debug(f"Auth proxy storage failed for user {self.user_id}: {e}")
        
        return False
    
    def _cache_credentials(self, credentials: Credentials) -> None:
        """
        Cache credentials in memory with TTL.
        """
        self._cached_credentials = credentials
        # Cache for 30 minutes or until token expiry, whichever is sooner
        cache_ttl = min(
            timedelta(minutes=30),
            timedelta(hours=1) if not credentials.expiry else 
            (credentials.expiry - datetime.utcnow())
        )
        self._cache_expiry = datetime.utcnow() + cache_ttl
        logger.debug(f"Cached credentials for user {self.user_id} until {self._cache_expiry}")
    
    async def revoke_credentials(self) -> bool:
        """
        Revoke and clear all stored credentials for the user.
        """
        try:
            # Clear local cache
            self._cached_credentials = None
            self._cache_expiry = None
            
            # Clear from auth proxy
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    await client.delete(
                        f"{self.auth_proxy_base_url}/revoke-tokens/{self.user_id}"
                    )
                logger.info(f"Revoked credentials from auth proxy for user {self.user_id}")
            except Exception as e:
                logger.debug(f"Auth proxy revocation failed for user {self.user_id}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke credentials for user {self.user_id}: {e}")
            return False
    
    async def is_authenticated(self) -> bool:
        """
        Check if user has valid Google authentication.
        """
        credentials = await self.get_credentials()
        return credentials is not None and not credentials.expired
    
    async def get_user_info(self) -> Optional[Dict[str, Any]]:
        """
        Get basic user info from Google OAuth.
        """
        credentials = await self.get_credentials()
        if not credentials:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {credentials.token}"}
                )
                
                if response.status_code == 200:
                    return response.json()
                    
        except Exception as e:
            logger.error(f"Failed to get user info for user {self.user_id}: {e}")
        
        return None


# Convenience functions for common use cases
async def get_google_credentials(user_id: int, scopes: Optional[list[str]] = None) -> Optional[Credentials]:
    """
    Convenience function to get Google credentials for a user.
    
    Args:
        user_id: The user ID
        scopes: Required OAuth scopes (uses default if None)
        
    Returns:
        Google OAuth credentials or None
    """
    helper = GoogleAuthHelper(user_id, scopes)
    return await helper.get_credentials()

async def is_user_authenticated(user_id: int) -> bool:
    """
    Check if a user has valid Google authentication.
    
    Args:
        user_id: The user ID
        
    Returns:
        True if user is authenticated
    """
    helper = GoogleAuthHelper(user_id)
    return await helper.is_authenticated()

async def revoke_user_credentials(user_id: int) -> bool:
    """
    Revoke Google credentials for a user.
    
    Args:
        user_id: The user ID
        
    Returns:
        True if revocation was successful
    """
    helper = GoogleAuthHelper(user_id)
    return await helper.revoke_credentials()
