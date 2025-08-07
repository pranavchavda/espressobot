#!/usr/bin/env python3
"""
Simple test of the LangGraph orchestrator
"""

import asyncio
import logging
import os
import sys

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
        from app.orchestrator import Orchestrator
        
        # Create orchestrator instance
        logger.info("\nCreating orchestrator...")
        orchestrator = Orchestrator()
        logger.info(f"✅ Orchestrator created with {len(orchestrator.agents)} agents")
        
        # List available agents
        logger.info("\nAvailable agents:")
        for name, agent in orchestrator.agents.items():
            logger.info(f"  - {name}: {agent.description[:60]}...")
        
        # Test queries (safe, read-only operations)
        test_queries = [
            "What can you help me with?",
            "Search for coffee products",
            "What's the current time?",
            "Show me low stock items",
        ]
        
        logger.info("\n" + "="*60)
        logger.info("TESTING QUERY PROCESSING")
        logger.info("="*60)
        
        for query in test_queries:
            logger.info(f"\nQuery: '{query}'")
            
            try:
                # Process query through orchestrator
                result = await orchestrator.process(
                    message=query,
                    conversation_id="test-conv-001",
                    user_id="1"
                )
                
                # Check result
                if result:
                    if isinstance(result, dict):
                        # Show relevant parts of response
                        if result.get("response"):
                            response_preview = str(result["response"])[:100]
                            if len(str(result["response"])) > 100:
                                response_preview += "..."
                            logger.info(f"✅ Response: {response_preview}")
                        
                        if result.get("agent"):
                            logger.info(f"   Handled by: {result['agent']}")
                    else:
                        # Just show preview of response
                        response_preview = str(result)[:100]
                        if len(str(result)) > 100:
                            response_preview += "..."
                        logger.info(f"✅ Response: {response_preview}")
                else:
                    logger.warning("⚠️  No response generated")
                    
            except AttributeError as e:
                # Try stream method if process doesn't exist
                logger.info("   Trying stream method...")
                chunks = []
                async for chunk in orchestrator.stream(
                    message=query,
                    conversation_id="test-conv-001",
                    user_id="1"
                ):
                    chunks.append(chunk)
                
                if chunks:
                    # Get the complete response
                    full_response = ""
                    agent_name = "unknown"
                    for chunk in chunks:
                        if chunk["type"] == "token":
                            full_response += chunk.get("content", "")
                            agent_name = chunk.get("agent", agent_name)
                    
                    if full_response:
                        response_preview = full_response[:100]
                        if len(full_response) > 100:
                            response_preview += "..."
                        logger.info(f"✅ Response: {response_preview}")
                        logger.info(f"   Handled by: {agent_name}")
                else:
                    logger.warning("⚠️  No response from stream")
                    
            except Exception as e:
                logger.error(f"❌ Error processing query: {e}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ Orchestrator testing complete!")
        logger.info("="*60)
        
    except ImportError as e:
        logger.error(f"❌ Could not import orchestrator: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(test_orchestrator())