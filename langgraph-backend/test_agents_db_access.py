#!/usr/bin/env python3
"""
Test Google Workspace and GA4 agents with direct database access
"""

import asyncio
import os
from dotenv import load_dotenv
import logging
import asyncpg

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_database_connection():
    """Test basic database connectivity"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Database Connection")
    logger.info("=" * 60)
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not found in environment")
        return False
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Check users with Google tokens
        users = await conn.fetch("""
            SELECT id, email, name,
                   google_access_token IS NOT NULL as has_google_token,
                   ga4_property_id,
                   ga4_enabled
            FROM users
            WHERE google_access_token IS NOT NULL 
               OR ga4_property_id IS NOT NULL
        """)
        
        if users:
            logger.info(f"✅ Found {len(users)} users with Google configuration:")
            for user in users:
                logger.info(f"  - User {user['id']}: {user['email'] or 'No email'}")
                logger.info(f"    Name: {user['name'] or 'No name'}")
                logger.info(f"    Has Google Token: {user['has_google_token']}")
                logger.info(f"    GA4 Property: {user['ga4_property_id'] or 'Not configured'}")
                logger.info(f"    GA4 Enabled: {user['ga4_enabled']}")
        else:
            logger.warning("⚠️  No users with Google tokens found in database")
            logger.info("   Users will need to authenticate via frontend first")
        
        await conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

async def test_google_workspace_agent():
    """Test Google Workspace agent initialization and database access"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Google Workspace Agent")
    logger.info("=" * 60)
    
    try:
        from app.agents.google_workspace_native_mcp import GoogleWorkspaceAgentNativeMCP
        
        # Initialize agent
        agent = GoogleWorkspaceAgentNativeMCP()
        logger.info(f"✅ Agent initialized: {agent.name}")
        
        # Test database access for user 1
        logger.info("\nTesting database access for user_id=1...")
        
        # Create a mock tool to test credentials
        from app.agents.google_workspace_native_mcp import GmailSearchTool
        tool = GmailSearchTool(user_id=1)
        
        # Try to get credentials (this will check database)
        creds = await tool._get_google_credentials()
        
        if creds:
            logger.info("✅ Successfully retrieved Google credentials from database")
            logger.info(f"   Token exists: {bool(creds.token)}")
            logger.info(f"   Refresh token exists: {bool(creds.refresh_token)}")
        else:
            logger.warning("⚠️  No Google credentials found for user_id=1")
            logger.info("   User needs to authenticate via frontend OAuth flow")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import Google Workspace agent: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing Google Workspace agent: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_ga4_agent():
    """Test GA4 Analytics agent initialization and database access"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing GA4 Analytics Agent")
    logger.info("=" * 60)
    
    try:
        from app.agents.ga4_analytics_native_mcp import GA4AnalyticsAgentNativeMCP
        
        # Initialize agent
        agent = GA4AnalyticsAgentNativeMCP()
        logger.info(f"✅ Agent initialized: {agent.name}")
        
        # Test database access for user 1
        logger.info("\nTesting database access for user_id=1...")
        
        # Create a mock tool to test credentials
        from app.agents.ga4_analytics_native_mcp import GA4RunReportTool
        tool = GA4RunReportTool(user_id=1)
        
        # Try to get credentials and property ID
        creds, property_id = await tool._get_ga4_credentials()
        
        if creds:
            logger.info("✅ Successfully retrieved GA4 credentials from database")
            logger.info(f"   Token exists: {bool(creds.token)}")
            logger.info(f"   Refresh token exists: {bool(creds.refresh_token)}")
            logger.info(f"   GA4 Property ID: {property_id or 'Not configured (will use env default)'}")
        else:
            logger.warning("⚠️  No GA4 credentials found for user_id=1")
            logger.info("   User needs to authenticate and enable GA4 in frontend")
        
        # Check environment variable fallback
        env_property = os.getenv("GA4_PROPERTY_ID")
        if env_property:
            logger.info(f"✅ Environment GA4_PROPERTY_ID configured: {env_property}")
        else:
            logger.warning("⚠️  No GA4_PROPERTY_ID in environment (fallback)")
        
        return True
        
    except ImportError as e:
        logger.error(f"❌ Failed to import GA4 Analytics agent: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing GA4 Analytics agent: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    logger.info("=" * 60)
    logger.info("TESTING GOOGLE AGENTS WITH UNIFIED DATABASE")
    logger.info("=" * 60)
    
    results = []
    
    # Test database connection
    results.append(("Database Connection", await test_database_connection()))
    
    # Test Google Workspace agent
    results.append(("Google Workspace Agent", await test_google_workspace_agent()))
    
    # Test GA4 Analytics agent
    results.append(("GA4 Analytics Agent", await test_ga4_agent()))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{test_name:30} {status}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 60)
    
    if all_passed:
        logger.info("✅ All tests passed! Agents are ready to use.")
        logger.info("\nNext steps:")
        logger.info("1. Users authenticate via frontend Google OAuth")
        logger.info("2. Frontend stores tokens in PostgreSQL users table")
        logger.info("3. Agents automatically access tokens from database")
        logger.info("4. Tokens are refreshed automatically when needed")
    else:
        logger.warning("⚠️  Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(main())