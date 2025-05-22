import asyncio
import unittest
import logging
from unittest.mock import patch, MagicMock
from collections import defaultdict # Import defaultdict

# Adjust the path to import from the project root
import sys
import os
# Assuming this test file is in the project root, so '..' is not needed for direct imports
# If 'simple_memory' etc. are in the root, direct import should work.

from simple_memory import SimpleMemoryServer
from embedding_service import EmbeddingService
from vector_store import VectorStore # Import VectorStore for patching its data

# Configure logging for the test
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG) # Show debug logs from services

class TestSimpleMemoryUserId(unittest.IsolatedAsyncioTestCase): # Use IsolatedAsyncioTestCase for async tests

    async def asyncSetUp(self):
        """Set up for each test."""
        # Patch VectorStore's _embeddings_data to ensure isolation
        # The VectorStore itself is a singleton, so we patch its data store.
        self.patcher_vector_store_data = patch.object(VectorStore, '_embeddings_data', new_callable=lambda: defaultdict(lambda: {'keys': [], 'vectors': []}))
        self.mock_vector_store_data = self.patcher_vector_store_data.start()
        
        # Patch the global memory_store in simple_memory
        self.patcher_simple_memory_store = patch('simple_memory.memory_store', new_callable=dict)
        self.mock_simple_memory_store = self.patcher_simple_memory_store.start()

        self.memory_server = SimpleMemoryServer() 
        
        self.mock_embedding_service = MagicMock(spec=EmbeddingService)
        self.mock_embedding_service.get_embedding.return_value = [0.1] * 768 
        self.memory_server.embedding_service = self.mock_embedding_service
        # Also ensure the vector_store instance within memory_server uses this patched data or is itself controlled
        # Since VectorStore is a singleton and we patched its class-level _embeddings_data, this should be covered.

    async def asyncTearDown(self):
        """Clean up after each test."""
        self.patcher_vector_store_data.stop()
        self.patcher_simple_memory_store.stop()

    async def test_store_and_retrieve_with_string_user_id(self):
        user_id_str = "1"
        memory_key = "breville_sale_info"
        memory_value = "The Breville barista express sale ends December 31st"
        query = "When does the Breville sale end?"

        logger.info(f"Test: Storing memory for user_id='{user_id_str}', key='{memory_key}'")
        store_result = await self.memory_server.store_user_memory(user_id_str, memory_key, memory_value)
        
        self.assertTrue(store_result.get("success"), f"Failed to store memory: {store_result.get('message')}")
        self.mock_embedding_service.get_embedding.assert_any_call(memory_value) # Use assert_any_call if reset_mock isn't used precisely
        
        logger.info(f"Test: Retrieving memory for user_id='{user_id_str}' with query='{query}'")
        retrieved_memories = await self.memory_server.proactively_retrieve_memories(user_id_str, query)
        self.mock_embedding_service.get_embedding.assert_any_call(query)
        
        self.assertIsNotNone(retrieved_memories, "Proactive retrieval returned None")
        self.assertGreater(len(retrieved_memories), 0, "No memories retrieved proactively")
        self.assertIn(memory_value, retrieved_memories, "Stored memory value not found in proactive retrieval results")
        logger.info(f"Test: Successfully retrieved: {retrieved_memories}")

if __name__ == '__main__':
    unittest.main()
