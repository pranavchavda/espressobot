#!/usr/bin/env python3
"""
Test script to verify direct database access is working for Google agents.
This tests the credential retrieval without making actual API calls.
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import AsyncSessionLocal, init_db
from app.database.models import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_test_user():
    """Create a test user with mock Google credentials"""
    async with AsyncSessionLocal() as session:
        # Check if test user exists
        existing_user = await session.get(User, 1)
        if existing_user:
            logger.info("Test user already exists")
            return existing_user.id
        
        # Create test user with mock tokens
        user = User(
            email="test@example.com",
            name="Test User",
            google_access_token="mock_access_token",
            google_refresh_token="mock_refresh_token", 
            google_token_expiry=datetime.utcnow() + timedelta(hours=1),
            ga4_property_id="123456789"
        )
        
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        logger.info(f"Created test user with ID: {user.id}")
        return user.id

async def test_google_workspace_agent():
    """Test Google Workspace agent initialization"""
    try:
        from app.agents.google_workspace_native_mcp import GoogleWorkspaceAgentNativeMCP
        
        agent = GoogleWorkspaceAgentNativeMCP()
        logger.info(f"✓ Google Workspace agent created: {agent.name}")
        
        # Test tool creation
        tools = agent._create_tools(user_id=1)
        logger.info(f"✓ Created {len(tools)} tools")
        
        # Test credential retrieval (this will fail with mock tokens but should not crash)
        if tools:
            tool = tools[0]  # GmailSearchTool
            creds = await tool._get_google_credentials()
            if creds is None:
                logger.info("✓ Credential retrieval returns None (expected with mock tokens)")
            else:
                logger.info(f"✓ Got credentials: {type(creds)}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Google Workspace agent test failed: {e}")
        return False

async def test_ga4_agent():
    """Test GA4 Analytics agent initialization"""
    try:
        from app.agents.ga4_analytics_native_mcp import GA4AnalyticsAgentNativeMCP
        
        agent = GA4AnalyticsAgentNativeMCP()
        logger.info(f"✓ GA4 Analytics agent created: {agent.name}")
        
        # Test tool creation
        tools = agent._create_tools(user_id=1)
        logger.info(f"✓ Created {len(tools)} tools")
        
        # Test credential retrieval (this will fail with mock tokens but should not crash)
        if tools:
            tool = tools[0]  # GA4RunReportTool
            creds, property_id = await tool._get_ga4_credentials()
            if creds is None:
                logger.info("✓ Credential retrieval returns None (expected with mock tokens)")
            else:
                logger.info(f"✓ Got credentials: {type(creds)}, property_id: {property_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ GA4 Analytics agent test failed: {e}")
        return False

async def test_database_operations():
    """Test basic database operations"""
    try:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, 1)
            if user:
                logger.info(f"✓ Can read user: {user.email}")
                logger.info(f"✓ Google tokens present: {bool(user.google_access_token)}")
                logger.info(f"✓ GA4 property ID: {user.ga4_property_id}")
                return True
            else:
                logger.error("✗ Test user not found")
                return False
    except Exception as e:
        logger.error(f"✗ Database operation failed: {e}")
        return False

async def main():
    """Run all tests"""
    logger.info("=== Testing Direct Database Access ===")
    
    # Initialize database
    try:
        await init_db()
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        return
    
    # Create test user
    try:
        user_id = await create_test_user()
        logger.info(f"✓ Test user ready: {user_id}")
    except Exception as e:
        logger.error(f"✗ Test user creation failed: {e}")
        return
    
    # Run tests
    tests = [
        ("Database Operations", test_database_operations),
        ("Google Workspace Agent", test_google_workspace_agent),
        ("GA4 Analytics Agent", test_ga4_agent),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Testing {test_name} ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"✗ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n=== Test Results ===")
    passed = 0
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
        if result:
            passed += 1
    
    logger.info(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        logger.info("🎉 All tests passed! Direct database access is working.")
    else:
        logger.info("⚠️  Some tests failed. Check the logs above.")

if __name__ == "__main__":
    asyncio.run(main())