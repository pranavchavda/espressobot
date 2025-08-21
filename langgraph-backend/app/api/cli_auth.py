"""
CLI Authentication API endpoints
Provides authentication support for the command-line interface
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import uuid
import json
import hashlib
import hmac
import jwt
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional
import os

# Initialize router
router = APIRouter(prefix="/api/auth/cli", tags=["CLI Authentication"])

# In-memory storage for CLI tokens (in production, use Redis or database)
cli_token_store: Dict[str, Dict] = {}

class CLITokenRequest(BaseModel):
    cli_token: str

class CLITokenResponse(BaseModel):
    access_token: str
    user_email: str
    expires_at: str

def generate_cli_token(user_id: str, user_email: str, access_token: str) -> str:
    """Generate a secure CLI token"""
    # Create a unique token
    token_data = {
        "user_id": user_id,
        "user_email": user_email,
        "access_token": access_token,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(minutes=10)).isoformat()  # 10 minute expiry
    }
    
    # Generate secure token
    cli_token = str(uuid.uuid4())
    
    # Store token data
    cli_token_store[cli_token] = token_data
    
    return cli_token

def cleanup_expired_tokens():
    """Remove expired CLI tokens"""
    now = datetime.utcnow()
    expired_tokens = []
    
    for token, data in cli_token_store.items():
        expires_at = datetime.fromisoformat(data["expires_at"])
        if now > expires_at:
            expired_tokens.append(token)
    
    for token in expired_tokens:
        del cli_token_store[token]

async def validate_jwt_token(jwt_token: str) -> Optional[Dict]:
    """Validate JWT token and extract user data"""
    try:
        # For now, decode without verification since we don't have the secret
        # In production, you'd verify with the actual JWT secret
        decoded = jwt.decode(jwt_token, options={"verify_signature": False})
        
        # Check if token has expired
        if 'exp' in decoded:
            exp_timestamp = decoded['exp']
            if datetime.utcnow().timestamp() > exp_timestamp:
                raise HTTPException(status_code=400, detail="JWT token has expired")
        
        # Extract user information
        return {
            "user_id": str(decoded.get('id', decoded.get('sub', 'unknown'))),
            "email": decoded.get('email', 'unknown@example.com'),
            "name": decoded.get('name', 'Unknown User')
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="JWT token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JWT token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token validation error: {str(e)}")

@router.post("/generate-token")
async def generate_cli_token_endpoint(request: Request):
    """Generate CLI token for authenticated web user"""
    
    # Clean up expired tokens first
    cleanup_expired_tokens()
    
    # Get user info from session/cookies (implement based on your auth system)
    # This is a placeholder - implement based on your actual authentication
    user_data = await get_user_from_session(request)
    
    if not user_data:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Generate CLI token
    cli_token = generate_cli_token(
        user_id=user_data["user_id"],
        user_email=user_data["email"], 
        access_token=user_data.get("access_token", "")
    )
    
    return {
        "cli_token": cli_token,
        "expires_in": 600  # 10 minutes
    }

@router.post("/validate", response_model=CLITokenResponse)
async def validate_cli_token(request: CLITokenRequest):
    """Validate CLI token and return access credentials"""
    
    cli_token = request.cli_token
    
    # First, try to validate as a JWT token (direct from web interface)
    if cli_token.startswith('eyJ'):  # JWT tokens start with 'eyJ'
        try:
            # Validate JWT token directly
            user_data = await validate_jwt_token(cli_token)
            if user_data:
                return CLITokenResponse(
                    access_token=cli_token,  # Use JWT as access token
                    user_email=user_data["email"],
                    expires_at=(datetime.utcnow() + timedelta(days=7)).isoformat()  # JWT expiry
                )
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JWT token: {str(e)}")
    
    # Clean up expired tokens first
    cleanup_expired_tokens()
    
    # Fall back to CLI token store lookup
    if cli_token not in cli_token_store:
        raise HTTPException(status_code=400, detail="Invalid or expired CLI token")
    
    token_data = cli_token_store[cli_token]
    
    # Check if token has expired
    expires_at = datetime.fromisoformat(token_data["expires_at"])
    if datetime.utcnow() > expires_at:
        del cli_token_store[cli_token]
        raise HTTPException(status_code=400, detail="CLI token has expired")
    
    # Remove token after use (one-time use)
    del cli_token_store[cli_token]
    
    return CLITokenResponse(
        access_token=token_data["access_token"],
        user_email=token_data["user_email"],
        expires_at=token_data["expires_at"]
    )

async def get_user_from_session(request: Request) -> Optional[Dict]:
    """Get user data from session - implement based on your auth system"""
    
    # Placeholder implementation - replace with your actual auth logic
    # This should check cookies, JWT tokens, or session data
    
    # Example using cookies (adjust based on your implementation):
    auth_token = request.cookies.get("auth_token") or request.headers.get("Authorization")
    
    if not auth_token:
        return None
    
    # Validate token and get user data
    # This is where you'd integrate with your existing auth system
    try:
        # Mock user data - replace with actual user lookup
        return {
            "user_id": "1",
            "email": "user@example.com",
            "access_token": auth_token.replace("Bearer ", "") if auth_token.startswith("Bearer ") else auth_token
        }
    except Exception:
        return None

@router.get("/status")
async def get_auth_status(request: Request):
    """Check authentication status"""
    user_data = await get_user_from_session(request)
    
    if not user_data:
        return {
            "authenticated": False,
            "user_email": None
        }
    
    return {
        "authenticated": True,
        "user_email": user_data["email"]
    }

@router.post("/logout")
async def logout():
    """Logout endpoint for CLI"""
    # Since CLI tokens are short-lived and one-time use,
    # this is mainly for completeness
    return {"message": "Logged out successfully"}