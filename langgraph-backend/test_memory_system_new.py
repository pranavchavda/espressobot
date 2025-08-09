#\!/usr/bin/env python3
"""Test memory extraction and injection system"""

import asyncio
import logging
import json
from app.orchestrator_direct import DirectOrchestrator
from langchain_core.messages import HumanMessage, AIMessage
from app.state.graph_state import GraphState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_memory_system():
    """Test memory extraction and injection"""
    
    # Create orchestrator
    orchestrator = DirectOrchestrator()
    
    # Initialize memory node
    await orchestrator.memory_node.initialize()
    
    # Test 1: Memory Extraction
    logger.info("\n=== TEST 1: Memory Extraction ===")
    
    # Create a test conversation with extractable memories
    test_messages = [
        HumanMessage(content="Hi, my name is TestUser and I prefer dark roast coffee"),
        AIMessage(content="Nice to meet you TestUser\! I'll remember your preference for dark roast coffee."),
        HumanMessage(content="I usually order a double shot espresso in the morning"),
        AIMessage(content="Great choice\! Double shot espresso is perfect for morning energy.")
    ]
    
    # Extract memories
    memories = await orchestrator.memory_node.extraction_service.extract_memories_from_conversation(
        test_messages, 
        user_id="test_user_123"
    )
    
    logger.info(f"Extracted {len(memories)} memories:")
    for mem in memories:
        logger.info(f"  - {mem.content} (category: {mem.category}, importance: {mem.importance_score})")
    
    # Test 2: Memory Loading/Injection
    logger.info("\n=== TEST 2: Memory Loading/Injection ===")
    
    # Create a state with user message
    state = {
        "messages": [HumanMessage(content="What kind of coffee do you recommend for me?")],
        "user_id": "1",  # Use user ID 1 which has existing memories
        "thread_id": "test-memory-injection"
    }
    
    # Load memory context
    state = await orchestrator.memory_node.load_memory_context(state)
    
    logger.info(f"Loaded {len(state.get('memory_context', []))} relevant memories:")
    for mem in state.get('memory_context', [])[:5]:
        logger.info(f"  - {mem['content']} (similarity: {mem.get('similarity', 'N/A')})")
    
    # Test 3: Full Orchestrator Flow with Memory
    logger.info("\n=== TEST 3: Full Orchestrator Flow with Memory ===")
    
    # Process request with memory context
    result_state = await orchestrator.process_request(state)
    
    # Check if memory was used in response
    if result_state.get("memory_context"):
        logger.info(f"✅ Memory context was loaded and available during processing")
        logger.info(f"   {len(result_state['memory_context'])} memories were available")
    else:
        logger.warning("⚠️ No memory context was loaded")
    
    # Check the response
    last_msg = result_state["messages"][-1] if result_state["messages"] else None
    if last_msg and isinstance(last_msg, AIMessage):
        logger.info(f"\nOrchestrator response: {last_msg.content[:200]}...")
    
    # Close resources
    await orchestrator.memory_node.close()
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_memory_system())
    if success:
        logger.info("\n✅ Memory system test completed successfully\!")
    else:
        logger.error("\n❌ Memory system test failed\!")
    exit(0 if success else 1)
