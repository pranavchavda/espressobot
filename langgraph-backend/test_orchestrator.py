#!/usr/bin/env python3
"""
Test the LangGraph orchestrator with all agents
"""

import asyncio
import logging
import os
import sys
from langchain_core.messages import HumanMessage, AIMessage

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

# Disable MCP servers for testing
os.environ["DISABLE_MCP_SERVER"] = "true"

async def test_orchestrator():
    """Test the orchestrator with various queries"""
    
    logger.info("="*60)
    logger.info("TESTING LANGGRAPH ORCHESTRATOR")
    logger.info("="*60)
    
    try:
        from app.orchestrator import create_graph
        
        # Create the graph
        logger.info("\nCreating orchestrator graph...")
        graph = create_graph()
        logger.info("✅ Graph created successfully")
        
        # Test queries (safe, read-only operations)
        test_queries = [
            # General query
            ("What can you help me with?", "general"),
            
            # Product queries (read-only)
            ("Search for coffee machines", "products"),
            ("Show me products under $100", "products"),
            
            # Sales/Analytics queries
            ("What were yesterday's sales?", "sales"),
            ("Show me recent orders", "orders"),
            
            # Inventory query
            ("Which products are low in stock?", "inventory"),
            
            # Integration query
            ("What integrations are available?", "integrations"),
            
            # Utility query  
            ("What time is it?", "utility"),
        ]
        
        logger.info("\n" + "="*60)
        logger.info("TESTING QUERY ROUTING")
        logger.info("="*60)
        
        for query, expected_agent in test_queries:
            logger.info(f"\nQuery: '{query}'")
            logger.info(f"Expected agent: {expected_agent}")
            
            # Create initial state
            state = {
                "messages": [HumanMessage(content=query)],
                "user_id": "1",
                "last_agent": None,
                "context": {}
            }
            
            try:
                # Run the graph
                result = await graph.ainvoke(state)
                
                # Check result
                if result.get("messages"):
                    last_message = result["messages"][-1]
                    if isinstance(last_message, AIMessage):
                        # Get agent that handled it
                        agent_used = result.get("last_agent", "unknown")
                        logger.info(f"✅ Handled by: {agent_used}")
                        
                        # Show preview of response
                        response_preview = last_message.content[:100]
                        if len(last_message.content) > 100:
                            response_preview += "..."
                        logger.info(f"   Response: {response_preview}")
                    else:
                        logger.warning("⚠️  No AI response generated")
                else:
                    logger.warning("⚠️  No messages in result")
                    
            except Exception as e:
                logger.error(f"❌ Error processing query: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("TESTING MULTI-TURN CONVERSATION")
        logger.info("="*60)
        
        # Test a multi-turn conversation
        conversation = [
            "Search for espresso machines",
            "Show me the ones under $500",
            "Which one has the best reviews?"
        ]
        
        state = {
            "messages": [],
            "user_id": "1",
            "last_agent": None,
            "context": {}
        }
        
        for turn, query in enumerate(conversation, 1):
            logger.info(f"\nTurn {turn}: '{query}'")
            
            # Add user message
            state["messages"].append(HumanMessage(content=query))
            
            try:
                # Run the graph
                result = await graph.ainvoke(state)
                state = result  # Update state with result
                
                # Check response
                if result.get("messages"):
                    last_message = result["messages"][-1]
                    if isinstance(last_message, AIMessage):
                        agent_used = result.get("last_agent", "unknown")
                        logger.info(f"✅ Handled by: {agent_used}")
                    else:
                        logger.warning("⚠️  No AI response")
                        
            except Exception as e:
                logger.error(f"❌ Error in turn {turn}: {e}")
                break
        
        logger.info("\n" + "="*60)
        logger.info("✅ Orchestrator testing complete!")
        logger.info("="*60)
        
    except ImportError as e:
        logger.error(f"❌ Could not import orchestrator: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())