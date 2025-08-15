#!/usr/bin/env python3
"""Test async agent calls in progressive orchestrator"""
import asyncio
import logging
import sys
import os

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '.')

async def test_agent_call():
    """Test calling an agent directly"""
    try:
        # Import orchestrator
        from app.orchestrator_progressive import get_orchestrator
        from langchain_core.messages import HumanMessage, SystemMessage
        
        # Get orchestrator
        orchestrator = await get_orchestrator()
        logger.info(f"Got orchestrator with {len(orchestrator.agents)} agents")
        
        # Get products agent
        if "products" in orchestrator.agents:
            agent = orchestrator.agents["products"]
            logger.info(f"Got products agent: {agent.name}")
            
            # Create test state
            state = {
                "messages": [
                    SystemMessage(content="You are being called by the orchestrator with a specific task."),
                    HumanMessage(content="Find the Breville Barista Express")
                ],
                "user_id": "test",
                "thread_id": "test-thread",
                "orchestrator_context": {}
            }
            
            logger.info("Calling agent with test state...")
            
            # Call agent - this is where it might hang
            try:
                result = await asyncio.wait_for(agent(state), timeout=10)
                logger.info(f"Agent returned: {type(result)}")
                
                if isinstance(result, dict):
                    logger.info(f"Result keys: {result.keys()}")
                    if "messages" in result:
                        logger.info(f"Got {len(result['messages'])} messages")
                        for msg in result['messages'][-2:]:  # Last 2 messages
                            logger.info(f"  - {msg.__class__.__name__}: {str(msg.content)[:100]}")
                
            except asyncio.TimeoutError:
                logger.error("Agent call timed out after 10 seconds!")
                return False
            
            return True
            
        else:
            logger.error("Products agent not found!")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return False

async def main():
    """Run the test"""
    success = await test_agent_call()
    if success:
        logger.info("✅ Agent call test passed!")
    else:
        logger.error("❌ Agent call test failed!")
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)