#!/usr/bin/env python3
"""
Test script to verify orchestrator optimization - should only make ONE API call
when responding directly (not routing to an agent).
"""

import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock, patch
import json
from app.orchestrator_direct import DirectOrchestrator
from langchain_core.messages import HumanMessage, AIMessage

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_direct_response_optimization():
    """Test that orchestrator uses routing response directly without second API call"""
    
    # Create orchestrator
    orchestrator = DirectOrchestrator()
    
    # Track API calls
    api_call_count = 0
    api_calls = []
    
    # Mock the model's ainvoke to track calls
    original_ainvoke = orchestrator.model.ainvoke
    
    async def mock_ainvoke(messages):
        nonlocal api_call_count, api_calls
        api_call_count += 1
        
        # Log the system prompt (first message)
        if messages and isinstance(messages, list) and len(messages) > 0:
            system_msg = messages[0].get("content", "") if isinstance(messages[0], dict) else ""
            # Truncate for logging
            system_preview = system_msg[:100] + "..." if len(system_msg) > 100 else system_msg
            api_calls.append({
                "call_number": api_call_count,
                "system_prompt_preview": system_preview,
                "message_count": len(messages)
            })
            logger.info(f"API Call #{api_call_count}: {system_preview}")
        
        # Return a routing decision with a complete response
        if "routing" in str(messages[0]).lower() or "specialist" in str(messages[0]).lower():
            # This is the routing call - return a complete response
            response_json = json.dumps({
                "action": "respond",
                "message": "Hello! I'm EspressoBot, your coffee assistant powered by GPT-5. I can help you with product searches, pricing, inventory management, and much more. How can I assist you today?"
            })
            
            mock_response = MagicMock()
            mock_response.content = response_json
            return mock_response
        else:
            # This shouldn't happen with our optimization
            logger.warning("UNEXPECTED: Second API call detected!")
            mock_response = MagicMock()
            mock_response.content = "This is a second API response that shouldn't be needed."
            return mock_response
    
    # Patch the model
    orchestrator.model.ainvoke = mock_ainvoke
    
    # Create a test state
    state = {
        "messages": [
            HumanMessage(content="Hello, what can you help me with?")
        ],
        "thread_id": "test-thread-123",
        "user_id": "test-user"
    }
    
    # Process the request
    logger.info("Processing test request...")
    result_state = await orchestrator.process_request(state)
    
    # Check results
    logger.info(f"\n=== RESULTS ===")
    logger.info(f"Total API calls made: {api_call_count}")
    logger.info(f"API call details: {json.dumps(api_calls, indent=2)}")
    
    # Verify we have a response
    if result_state.get("messages"):
        last_msg = result_state["messages"][-1]
        if isinstance(last_msg, AIMessage):
            logger.info(f"Response received: {last_msg.content[:100]}...")
            logger.info(f"Response metadata: {last_msg.metadata}")
    
    # ASSERTION: Should only make ONE API call
    if api_call_count == 1:
        logger.info("✅ SUCCESS: Only one API call made (optimized!)")
        return True
    else:
        logger.error(f"❌ FAILURE: Made {api_call_count} API calls (should be 1)")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_direct_response_optimization())
    exit(0 if success else 1)