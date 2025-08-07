#!/usr/bin/env python3
"""
Quick initialization test for all LangGraph agents.
Tests that agents can be imported and initialized without errors.
"""

import asyncio
import logging
import os
import sys
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Disable MCP server startup
os.environ["DISABLE_MCP_SERVER"] = "true"

async def test_agent_initialization():
    """Test initialization of all agents"""
    
    # List of agents to test (module_name, class_name, display_name)
    agents = [
        ("general", "GeneralAgent", "General Agent"),
        ("products_native_mcp", "ProductsAgentNativeMCP", "Products Agent"),
        ("product_mgmt_native_mcp", "ProductManagementAgentNativeMCP", "Product Management"),
        ("pricing_native_mcp", "PricingAgentNativeMCP", "Pricing Agent"),
        ("inventory_native_mcp", "InventoryAgentNativeMCP", "Inventory Agent"),
        ("media_native_mcp", "MediaAgentNativeMCP", "Media Agent"),
        ("features_native_mcp", "FeaturesAgentNativeMCP", "Features Agent"),
        ("sales_native_mcp", "SalesAgentNativeMCP", "Sales Agent"),
        ("orders_native_mcp", "OrdersAgentNativeMCP", "Orders Agent"),
        ("integrations_native_mcp", "IntegrationsAgentNativeMCP", "Integrations Agent"),
        ("graphql_native_mcp", "GraphQLAgentNativeMCP", "GraphQL Agent"),
        ("google_workspace_native_mcp", "GoogleWorkspaceAgentNativeMCP", "Google Workspace"),
        ("ga4_analytics_native_mcp", "GA4AnalyticsAgentNativeMCP", "GA4 Analytics"),
        ("utility_native_mcp", "UtilityAgentNativeMCP", "Utility Agent"),
    ]
    
    results = []
    passed = 0
    failed = 0
    
    logger.info("="*60)
    logger.info("TESTING AGENT INITIALIZATION")
    logger.info("="*60)
    
    for module_name, class_name, display_name in agents:
        try:
            # Import the module
            module = __import__(f"app.agents.{module_name}", fromlist=[class_name])
            
            # Get the class
            agent_class = getattr(module, class_name, None)
            if not agent_class:
                logger.error(f"❌ {display_name:30} - Class {class_name} not found in module")
                results.append((display_name, "CLASS_NOT_FOUND"))
                failed += 1
                continue
            
            # Initialize the agent
            agent = agent_class()
            
            # Check basic attributes
            if not hasattr(agent, 'name'):
                logger.warning(f"⚠️  {display_name:30} - Missing 'name' attribute")
            
            if not hasattr(agent, 'description'):
                logger.warning(f"⚠️  {display_name:30} - Missing 'description' attribute")
            
            # Check if it has the callable method
            if not hasattr(agent, '__call__'):
                logger.warning(f"⚠️  {display_name:30} - Missing '__call__' method")
            
            logger.info(f"✅ {display_name:30} - Initialized successfully")
            results.append((display_name, "PASSED"))
            passed += 1
            
        except ImportError as e:
            logger.error(f"❌ {display_name:30} - Import error: {e}")
            results.append((display_name, f"IMPORT_ERROR"))
            failed += 1
            
        except Exception as e:
            logger.error(f"❌ {display_name:30} - Initialization error: {e}")
            results.append((display_name, f"INIT_ERROR"))
            failed += 1
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    logger.info(f"Total agents tested: {len(agents)}")
    logger.info(f"✅ Passed: {passed}")
    logger.info(f"❌ Failed: {failed}")
    logger.info("="*60)
    
    if failed == 0:
        logger.info("🎉 All agents initialized successfully!")
    else:
        logger.warning(f"⚠️  {failed} agents failed initialization")
    
    return passed, failed


async def test_agent_routing():
    """Test that agents respond to appropriate queries"""
    
    from langchain_core.messages import HumanMessage
    
    test_cases = [
        ("What products do you have?", ["products", "product_mgmt"]),
        ("Show me today's sales", ["sales", "orders"]),
        ("Update pricing for SKU-123", ["pricing"]),
        ("Check inventory levels", ["inventory"]),
        ("Add product images", ["media"]),
        ("What's the weather?", ["general", "utility"]),
        ("Check my email", ["google_workspace"]),
        ("Show website traffic", ["ga4_analytics"]),
    ]
    
    logger.info("\n" + "="*60)
    logger.info("TESTING AGENT ROUTING")
    logger.info("="*60)
    
    # Import router
    try:
        from app.agents.router import AgentRouter
        router = AgentRouter()
        
        for query, expected_agents in test_cases:
            state = {
                "messages": [HumanMessage(content=query)],
                "user_id": 1,
                "last_agent": None
            }
            
            # Get selected agent
            selected = router.route(state)
            logger.info(f"Query: '{query[:40]}...'")
            logger.info(f"  → Selected: {selected}")
            
            # Check if selection makes sense
            if any(agent in selected for agent in expected_agents):
                logger.info(f"  ✅ Correct routing")
            else:
                logger.warning(f"  ⚠️  Expected one of: {expected_agents}")
    
    except ImportError:
        logger.warning("Router not available - skipping routing tests")
    except Exception as e:
        logger.error(f"Error testing routing: {e}")


async def main():
    """Main test runner"""
    
    # Test initialization
    passed, failed = await test_agent_initialization()
    
    # Test routing if all agents initialized
    if failed == 0:
        await test_agent_routing()
    
    logger.info("\n✅ Testing complete!")


if __name__ == "__main__":
    asyncio.run(main())