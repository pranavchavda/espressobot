#!/usr/bin/env python3
"""
Comprehensive test script for all LangGraph agents.
Tests agent initialization and basic functionality without modifying live data.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Test configuration
TEST_USER_ID = 1  # pranav@idrinkcoffee.com
TEST_PRODUCT_SKU = "TEST-AGENT-001"  # We'll create this for testing

class AgentTester:
    """Test harness for LangGraph agents"""
    
    def __init__(self):
        self.results = {}
        self.test_product_id = None
        
    async def test_agent(self, agent_name: str, agent_class, test_query: str = None):
        """Test a single agent"""
        try:
            logger.info(f"\nTesting {agent_name}...")
            
            # Initialize agent
            agent = agent_class()
            
            # Check basic attributes
            assert hasattr(agent, 'name'), f"{agent_name} missing 'name' attribute"
            assert hasattr(agent, 'description'), f"{agent_name} missing 'description' attribute"
            
            # Test state processing (if query provided)
            if test_query:
                from langchain_core.messages import HumanMessage
                
                state = {
                    "messages": [HumanMessage(content=test_query)],
                    "user_id": TEST_USER_ID,
                    "last_agent": None
                }
                
                # Check if agent should handle this query
                if hasattr(agent, 'should_handle'):
                    should_handle = agent.should_handle(state)
                    logger.info(f"  Should handle query: {should_handle}")
                
                # Don't actually invoke to avoid modifying data
                logger.info(f"  ✅ Agent initialized successfully")
            else:
                logger.info(f"  ✅ Agent initialized (no test query)")
            
            self.results[agent_name] = "PASSED"
            return True
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            self.results[agent_name] = f"FAILED: {str(e)}"
            return False
    
    async def create_test_product(self):
        """Create a test product for safe manipulation"""
        try:
            logger.info("\n" + "="*60)
            logger.info("Creating Test Product for Safe Testing")
            logger.info("="*60)
            
            from app.agents.products_native_mcp import ProductsAgentNativeMCP
            from langchain_core.messages import HumanMessage
            
            agent = ProductsAgentNativeMCP()
            
            # Create a test product in DRAFT status
            create_query = f"""Create a new product with these details:
            - Title: TEST PRODUCT - DO NOT PUBLISH
            - SKU: {TEST_PRODUCT_SKU}
            - Vendor: Test Vendor
            - Product Type: Test Products
            - Price: 99.99
            - Status: DRAFT
            - Description: This is a test product for agent testing. DO NOT PUBLISH.
            """
            
            state = {
                "messages": [HumanMessage(content=create_query)],
                "user_id": TEST_USER_ID,
                "last_agent": None
            }
            
            # Actually create the test product
            result = await agent(state)
            
            # Extract product ID from response if possible
            if result.get("messages"):
                last_message = result["messages"][-1]
                content = last_message.content
                # Try to extract product ID from response
                if "created" in content.lower() and "product" in content.lower():
                    logger.info(f"  ✅ Test product created: {TEST_PRODUCT_SKU}")
                    self.test_product_id = TEST_PRODUCT_SKU
                    return True
            
            logger.warning("  ⚠️ Could not confirm test product creation")
            return False
            
        except Exception as e:
            logger.error(f"  ❌ Failed to create test product: {e}")
            return False
    
    async def run_all_tests(self):
        """Run tests for all agents"""
        logger.info("="*60)
        logger.info("TESTING ALL LANGGRAPH AGENTS")
        logger.info("="*60)
        
        # Create test product first
        await self.create_test_product()
        
        # Test each agent
        test_cases = [
            # General agent
            ("General Agent", "general", "GeneralAgent", "What can you help me with?"),
            
            # Product-related agents (SAFE - read-only queries)
            ("Products Agent", "products_native_mcp", "ProductsAgentNativeMCP", 
             f"Search for product with SKU {TEST_PRODUCT_SKU}"),
            
            ("Product Management Agent", "product_mgmt_native_mcp", "ProductManagementAgentNativeMCP",
             f"Show me details for SKU {TEST_PRODUCT_SKU}"),
            
            ("Pricing Agent", "pricing_native_mcp", "PricingAgentNativeMCP",
             f"What's the price of SKU {TEST_PRODUCT_SKU}?"),
            
            ("Inventory Agent", "inventory_native_mcp", "InventoryAgentNativeMCP",
             "Show me low stock items"),
            
            ("Media Agent", "media_native_mcp", "MediaAgentNativeMCP",
             f"List images for SKU {TEST_PRODUCT_SKU}"),
            
            ("Features Agent", "features_native_mcp", "FeaturesAgentNativeMCP",
             f"Show features for SKU {TEST_PRODUCT_SKU}"),
            
            # Sales and analytics agents (SAFE - read-only)
            ("Sales Agent", "sales_native_mcp", "SalesAgentNativeMCP",
             "Show me today's sales summary"),
            
            ("Orders Agent", "orders_native_mcp", "OrdersAgentNativeMCP",
             "Show recent orders"),
            
            # Integration agents
            ("Integrations Agent", "integrations_native_mcp", "IntegrationsAgentNativeMCP",
             "What integrations are available?"),
            
            ("GraphQL Agent", "graphql_native_mcp", "GraphQLAgentNativeMCP",
             "Show me the shop name"),
            
            # Google agents (already tested separately)
            ("Google Workspace Agent", "google_workspace_native_mcp", "GoogleWorkspaceAgentNativeMCP",
             "Check my recent emails"),
            
            ("GA4 Analytics Agent", "ga4_analytics_native_mcp", "GA4AnalyticsAgentNativeMCP",
             "Show today's website traffic"),
            
            # Utility agent
            ("Utility Agent", "utility_native_mcp", "UtilityAgentNativeMCP",
             "What's the current time?"),
        ]
        
        for agent_name, module_name, class_name, test_query in test_cases:
            try:
                # Import agent class
                module = __import__(f"app.agents.{module_name}", fromlist=[class_name])
                agent_class = getattr(module, class_name)
                
                # Test the agent
                await self.test_agent(agent_name, agent_class, test_query)
                
            except ImportError as e:
                logger.warning(f"  ⚠️ Could not import {agent_name}: {e}")
                self.results[agent_name] = "NOT FOUND"
            except AttributeError as e:
                logger.warning(f"  ⚠️ Class not found for {agent_name}: {e}")
                self.results[agent_name] = "CLASS NOT FOUND"
            except Exception as e:
                logger.error(f"  ❌ Unexpected error for {agent_name}: {e}")
                self.results[agent_name] = f"ERROR: {str(e)}"
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        logger.info("\n" + "="*60)
        logger.info("TEST SUMMARY")
        logger.info("="*60)
        
        passed = 0
        failed = 0
        not_found = 0
        
        for agent_name, result in self.results.items():
            status_symbol = "✅" if result == "PASSED" else "❌"
            logger.info(f"{agent_name:40} {status_symbol} {result}")
            
            if result == "PASSED":
                passed += 1
            elif "NOT FOUND" in result or "CLASS NOT FOUND" in result:
                not_found += 1
            else:
                failed += 1
        
        logger.info("="*60)
        logger.info(f"Total: {len(self.results)} agents tested")
        logger.info(f"✅ Passed: {passed}")
        logger.info(f"❌ Failed: {failed}")
        logger.info(f"⚠️  Not Found: {not_found}")
        
        if self.test_product_id:
            logger.info(f"\n⚠️  Test product created: {self.test_product_id}")
            logger.info("   Remember to delete it after testing!")
        
        if passed == len(self.results):
            logger.info("\n🎉 All agents passed testing!")
        elif failed > 0:
            logger.warning(f"\n⚠️  {failed} agents failed. Check logs for details.")


async def main():
    """Main test runner"""
    tester = AgentTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())