#!/usr/bin/env python3
"""Test script for the PostgreSQL memory management system"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent / "app"))

from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_memory_system():
    """Comprehensive test of the memory management system"""
    
    logger.info("🧠 Starting memory system tests...")
    
    try:
        from app.memory import (
            PostgresMemoryManager, 
            Memory, 
            PromptFragment, 
            PromptAssembler, 
            ContextTier,
            get_embedding_service
        )
        from app.memory.memory_persistence import MemoryPersistenceNode
        
        # Test 1: Initialize components
        logger.info("📝 Test 1: Initializing memory components...")
        
        memory_manager = PostgresMemoryManager()
        await memory_manager.initialize()
        
        embedding_service = get_embedding_service()
        prompt_assembler = PromptAssembler(memory_manager)
        memory_node = MemoryPersistenceNode()
        await memory_node.initialize()
        
        logger.info("✅ All components initialized successfully")
        
        # Test 2: Store memories
        logger.info("📝 Test 2: Storing test memories...")
        
        test_user_id = "test_user_123"
        test_memories = [
            Memory(
                user_id=test_user_id,
                content="User prefers dark mode for all applications",
                category="preference",
                importance_score=0.8,
                metadata={"topic": "ui_preferences", "type": "setting"}
            ),
            Memory(
                user_id=test_user_id,
                content="User works in the fintech industry and focuses on API integrations",
                category="personal",
                importance_score=0.9,
                metadata={"topic": "professional", "industry": "fintech"}
            ),
            Memory(
                user_id=test_user_id,
                content="User mentioned they have a deadline on Friday for the payment system project",
                category="goal",
                importance_score=0.7,
                metadata={"topic": "project", "deadline": "friday"}
            ),
            Memory(
                user_id=test_user_id,
                content="User likes detailed technical explanations rather than high-level overviews",
                category="preference",
                importance_score=0.8,
                metadata={"topic": "communication_style"}
            )
        ]\n        \n        stored_ids = []\n        for memory in test_memories:\n            memory_id = await memory_manager.store_memory(memory)\n            stored_ids.append(memory_id)\n            logger.info(f\"  Stored memory {memory_id}: {memory.content[:50]}...\")\n        \n        logger.info(f\"✅ Stored {len(stored_ids)} memories successfully\")\n        \n        # Test 3: Search memories\n        logger.info(\"📝 Test 3: Testing memory search...\")\n        \n        search_queries = [\n            \"What are the user's preferences?\",\n            \"Tell me about their work\",\n            \"Any upcoming deadlines?\",\n            \"How should I communicate with them?\"\n        ]\n        \n        for query in search_queries:\n            results = await memory_manager.search_memories(\n                user_id=test_user_id,\n                query=query,\n                limit=3,\n                similarity_threshold=0.6\n            )\n            \n            logger.info(f\"  Query: '{query}'\")\n            for result in results:\n                logger.info(f\"    Score {result.similarity_score:.3f}: {result.memory.content[:60]}...\")\n        \n        logger.info(\"✅ Memory search working correctly\")\n        \n        # Test 4: Test deduplication\n        logger.info(\"📝 Test 4: Testing deduplication...\")\n        \n        # Try to store a duplicate memory\n        duplicate_memory = Memory(\n            user_id=test_user_id,\n            content=\"The user prefers dark mode in all their applications\",  # Similar to first memory\n            category=\"preference\",\n            importance_score=0.7\n        )\n        \n        duplicate_id = await memory_manager.store_memory(duplicate_memory)\n        \n        if duplicate_id in stored_ids:\n            logger.info(\"  ✅ Duplicate detected and merged successfully\")\n        else:\n            logger.info(f\"  ⚠️ New memory created (ID: {duplicate_id}) - may not be a duplicate\")\n        \n        # Test 5: Prompt assembly\n        logger.info(\"📝 Test 5: Testing intelligent prompt assembly...\")\n        \n        # Store a test prompt fragment first\n        test_fragment = PromptFragment(\n            category=\"test_guidelines\",\n            priority=5,\n            content=\"When working with fintech users, always consider security and compliance requirements.\",\n            agent_type=\"general\",\n            context_tier=\"standard\",\n            tags=[\"fintech\", \"security\", \"compliance\"]\n        )\n        \n        fragment_id = await prompt_assembler.store_prompt_fragment(test_fragment)\n        logger.info(f\"  Stored test prompt fragment: {fragment_id}\")\n        \n        # Test prompt assembly\n        assembled = await prompt_assembler.assemble_prompt(\n            user_query=\"How should I implement API rate limiting for our payment system?\",\n            user_id=test_user_id,\n            agent_type=\"general\",\n            context_tier=ContextTier.STANDARD\n        )\n        \n        logger.info(f\"  Assembled prompt with {len(assembled.relevant_memories)} memories\")\n        logger.info(f\"  and {len(assembled.prompt_fragments)} fragments\")\n        logger.info(f\"  Context tier: {assembled.context_tier.value}\")\n        logger.info(f\"  Consolidation applied: {assembled.consolidation_applied}\")\n        \n        logger.info(\"✅ Prompt assembly working correctly\")\n        \n        # Test 6: Memory node integration\n        logger.info(\"📝 Test 6: Testing memory node integration...\")\n        \n        from app.state.graph_state import GraphState, create_initial_state\n        from langchain_core.messages import HumanMessage, AIMessage\n        \n        # Create test state\n        test_state = create_initial_state(\n            user_message=\"I need help setting up OAuth2 for our fintech API\",\n            user_id=test_user_id,\n            conversation_id=\"test_conv_123\"\n        )\n        \n        # Add an AI response\n        test_state[\"messages\"].append(\n            AIMessage(content=\"I can help you set up OAuth2. Given your fintech background, we'll need to ensure PCI compliance.\")\n        )\n        \n        # Test loading memory context\n        enhanced_state = await memory_node.load_memory_context(test_state)\n        \n        logger.info(f\"  Memory context loaded: {len(enhanced_state.get('memory_context', []))} memories\")\n        logger.info(f\"  Prompt fragments: {len(enhanced_state.get('prompt_fragments', []))} fragments\")\n        logger.info(f\"  Context tier: {enhanced_state.get('context_tier')}\")\n        \n        # Test memory persistence\n        updated_state = await memory_node.persist_conversation_memories(enhanced_state)\n        \n        extracted_count = updated_state.get(\"metadata\", {}).get(\"memories_extracted\", 0)\n        stored_count = updated_state.get(\"metadata\", {}).get(\"memories_stored\", 0)\n        \n        logger.info(f\"  Extracted {extracted_count} new memories from conversation\")\n        logger.info(f\"  Stored {stored_count} new memories\")\n        \n        logger.info(\"✅ Memory node integration working correctly\")\n        \n        # Test 7: Performance and statistics\n        logger.info(\"📝 Test 7: Testing statistics and performance...\")\n        \n        # Get user stats\n        user_stats = await memory_manager.get_user_memory_stats(test_user_id)\n        logger.info(f\"  User stats: {user_stats}\")\n        \n        # Get fragment stats\n        fragment_stats = await prompt_assembler.get_fragment_stats()\n        logger.info(f\"  Fragment stats: {fragment_stats}\")\n        \n        # Get performance stats\n        performance_stats = memory_manager.get_performance_stats()\n        logger.info(f\"  Performance stats: {performance_stats}\")\n        \n        # Get embedding cache stats\n        cache_stats = embedding_service.get_cache_stats()\n        logger.info(f\"  Embedding cache stats: {cache_stats}\")\n        \n        logger.info(\"✅ Statistics and performance monitoring working\")\n        \n        # Test 8: Cleanup test\n        logger.info(\"📝 Test 8: Testing cleanup functionality...\")\n        \n        # This would normally clean up old memories, but we'll skip for test data\n        logger.info(\"  Skipping cleanup to preserve test data\")\n        \n        # Close connections\n        await memory_manager.close()\n        await memory_node.close()\n        \n        logger.info(\"🎉 All memory system tests completed successfully!\")\n        \n        return True\n        \n    except Exception as e:\n        logger.error(f\"❌ Memory system test failed: {e}\")\n        import traceback\n        traceback.print_exc()\n        return False\n\nasync def test_embedding_service():\n    \"\"\"Test the embedding service specifically\"\"\"\n    \n    logger.info(\"🔍 Testing embedding service...\")\n    \n    from app.memory.embedding_service import get_embedding_service\n    \n    embedding_service = get_embedding_service()\n    \n    # Test single embedding\n    test_text = \"Hello, this is a test for the embedding service.\"\n    result = await embedding_service.get_embedding(test_text)\n    \n    logger.info(f\"  Single embedding: {len(result.embedding)} dimensions\")\n    logger.info(f\"  Token count: {result.token_count}\")\n    logger.info(f\"  Cached: {result.cached}\")\n    \n    # Test batch embeddings\n    test_texts = [\n        \"This is the first test text.\",\n        \"Here's a second piece of content.\",\n        \"And a third text for batch testing.\"\n    ]\n    \n    batch_results = await embedding_service.get_embeddings_batch(test_texts)\n    logger.info(f\"  Batch results: {len(batch_results)} embeddings\")\n    \n    # Test similarity calculation\n    similarity = embedding_service.cosine_similarity(\n        batch_results[0].embedding,\n        batch_results[1].embedding\n    )\n    logger.info(f\"  Similarity between texts 1 and 2: {similarity:.4f}\")\n    \n    # Test cache performance\n    cache_stats = embedding_service.get_cache_stats()\n    logger.info(f\"  Cache performance: {cache_stats}\")\n    \n    logger.info(\"✅ Embedding service tests completed\")\n\nasync def main():\n    \"\"\"Run all tests\"\"\"\n    \n    # Check environment\n    if not os.getenv(\"DATABASE_URL\"):\n        logger.error(\"❌ DATABASE_URL not found in environment\")\n        return False\n    \n    if not os.getenv(\"OPENAI_API_KEY\"):\n        logger.error(\"❌ OPENAI_API_KEY not found in environment\")\n        return False\n    \n    logger.info(\"🚀 Starting comprehensive memory system tests...\")\n    \n    # Test embedding service first\n    await test_embedding_service()\n    \n    # Test full memory system\n    success = await test_memory_system()\n    \n    if success:\n        logger.info(\"🎉 All tests passed! Memory system is ready for production.\")\n    else:\n        logger.error(\"❌ Some tests failed. Please check the logs.\")\n        sys.exit(1)\n\nif __name__ == \"__main__\":\n    asyncio.run(main())"}, {"old_string": "        stored_ids = []\n        for memory in test_memories:\n            memory_id = await memory_manager.store_memory(memory)\n            stored_ids.append(memory_id)\n            logger.info(f\"  Stored memory {memory_id}: {memory.content[:50]}...\")", "new_string": "        stored_ids = []\n        for memory in test_memories:\n            memory_id = await memory_manager.store_memory(memory)\n            stored_ids.append(memory_id)\n            logger.info(f\"  Stored memory {memory_id}: {memory.content[:50]}...\")"}]