#!/usr/bin/env python3
"""Test the ProductsAgentNativeMCPSimple directly"""
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_products_agent():
    """Test the products agent directly"""
    from app.agents.products_native_mcp_simple import ProductsAgentNativeMCPSimple
    from langchain_core.messages import HumanMessage
    
    try:
        # Create agent
        agent = ProductsAgentNativeMCPSimple()
        
        # Create state
        state = {
            "messages": [
                HumanMessage(content="find Breville Barista Express")
            ],
            "user_id": "1",
            "thread_id": "test-direct"
        }
        
        # Call agent
        logger.info("Calling products agent...")
        result = await agent(state)
        
        # Check result
        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, 'content'):
                    logger.info(f"Response: {msg.content[:200]}...")
                    return True
        
        logger.error("No response from agent")
        return False
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_products_agent())
    print(f"\n{'✅' if success else '❌'} Test {'passed' if success else 'failed'}")