#!/usr/bin/env python3
"""
Test script for Google Authentication Bridge
This script tests the auth proxy API and auth helper functionality
"""
import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Add app to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.auth_helper import GoogleAuthHelper, get_google_credentials
from app.database.session import AsyncSessionLocal
from app.database.models import User
from sqlalchemy import select

async def test_auth_helper():
    """Test the GoogleAuthHelper functionality"""
    print("⚡ Testing GoogleAuthHelper...")
    
    # Test with a mock user ID
    test_user_id = 1
    
    try:
        # Initialize auth helper
        auth_helper = GoogleAuthHelper(
            user_id=test_user_id,
            required_scopes=[
                'https://www.googleapis.com/auth/gmail.readonly',
                'https://www.googleapis.com/auth/calendar'
            ]
        )
        
        print(f"✅ Created GoogleAuthHelper for user {test_user_id}")
        
        # Test authentication status
        is_authenticated = await auth_helper.is_authenticated()
        print(f"Authentication status: {'Authenticated' if is_authenticated else 'Not authenticated'}")
        
        # Test credential retrieval
        credentials = await auth_helper.get_credentials()
        if credentials:
            print("✅ Successfully retrieved credentials")
            print(f"   Token exists: {bool(credentials.token)}")
            print(f"   Refresh token exists: {bool(credentials.refresh_token)}")
            print(f"   Scopes: {list(credentials.scopes) if credentials.scopes else 'None'}")
            print(f"   Expired: {credentials.expired if credentials.expiry else 'Unknown'}")
        else:
            print("❌ No credentials found - user needs to authenticate")
        
        print("")
        
    except Exception as e:
        print(f"❌ Error testing auth helper: {e}")

async def test_database_connection():
    """Test database connection and user table access"""
    print("⚡ Testing database connection...")
    
    try:
        async with AsyncSessionLocal() as session:
            # Test basic query
            result = await session.execute(select(User).limit(1))
            user = result.scalar_one_or_none()
            
            if user:
                print(f"✅ Database connection successful")
                print(f"   Found user: {user.email} (ID: {user.id})")
                print(f"   Google tokens: {'Yes' if user.google_access_token else 'No'}")
                
                return user.id  # Return a real user ID for testing
            else:
                print("❌ No users found in database")
                return None
                
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

async def test_convenience_functions():
    """Test convenience functions"""
    print("⚡ Testing convenience functions...")
    
    test_user_id = 1
    
    try:
        # Test get_google_credentials function
        credentials = await get_google_credentials(test_user_id)
        print(f"get_google_credentials: {'Success' if credentials else 'No credentials'}")
        
        # Test is_user_authenticated function
        from app.agents.auth_helper import is_user_authenticated
        is_auth = await is_user_authenticated(test_user_id)
        print(f"is_user_authenticated: {is_auth}")
        
        print("")
        
    except Exception as e:
        print(f"❌ Error testing convenience functions: {e}")

async def test_redis_connection():
    """Test Redis connection for caching"""
    print("⚡ Testing Redis connection...")
    
    try:
        from app.api.auth_proxy import get_redis_client
        
        redis_client = await get_redis_client()
        if redis_client:
            print("✅ Redis connection successful")
            
            # Test basic Redis operations
            await redis_client.set("test_key", "test_value", ex=10)
            value = await redis_client.get("test_key")
            
            if value == "test_value":
                print("✅ Redis read/write operations working")
            else:
                print("❌ Redis read/write test failed")
                
            await redis_client.delete("test_key")
            
        else:
            print("❌ Redis connection failed - will use database fallback")
            
        print("")
        
    except Exception as e:
        print(f"❌ Redis test error: {e}")

def print_configuration():
    """Print current configuration"""
    print("⚡ Current Configuration:")
    print(f"   GOOGLE_CLIENT_ID: {'Set' if os.getenv('GOOGLE_CLIENT_ID') else 'Not set'}")
    print(f"   GOOGLE_CLIENT_SECRET: {'Set' if os.getenv('GOOGLE_CLIENT_SECRET') else 'Not set'}")
    print(f"   GA4_PROPERTY_ID: {os.getenv('GA4_PROPERTY_ID', 'Not set')}")
    print(f"   REDIS_URL: {os.getenv('REDIS_URL', 'redis://localhost:6379')}")
    print(f"   AUTH_PROXY_BASE_URL: {os.getenv('AUTH_PROXY_BASE_URL', 'http://localhost:8000/api/auth')}")
    print("")

async def main():
    """Main test function"""
    print("\n🧪 Google Authentication Bridge Test Suite")
    print("=" * 50)
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Print configuration
    print_configuration()
    
    # Run tests
    await test_redis_connection()
    user_id = await test_database_connection()
    await test_auth_helper()
    await test_convenience_functions()
    
    print("🏁 Test suite completed!")
    print("\nNext steps:")
    print("1. Ensure Google OAuth is configured with valid CLIENT_ID and CLIENT_SECRET")
    print("2. Set up Redis server (optional, will fallback to database)")
    print("3. Configure GA4_PROPERTY_ID for analytics access")
    print("4. Test frontend OAuth integration with /api/auth/store-tokens endpoint")
    print("5. Verify agents can access Google APIs through auth helper")

if __name__ == "__main__":
    asyncio.run(main())
