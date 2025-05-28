"""
Unit tests for the optimized memory service implementation.
"""
import os
import sys
import json
import unittest
import asyncio
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.memory_service import MemoryService, MemoryServiceError

class TestMemoryService(unittest.TestCase):
    """Test cases for the MemoryService class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test storage path
        self.test_storage_path = os.path.join(os.getcwd(), "test_storage", "memory")
        
        # Create a test instance with the test storage path
        with patch('services.config.service_config.get') as mock_get:
            mock_get.return_value = self.test_storage_path
            self.memory_service = MemoryService()
        
        # Ensure test directory exists and is empty
        os.makedirs(self.test_storage_path, exist_ok=True)
        for file in os.listdir(self.test_storage_path):
            os.remove(os.path.join(self.test_storage_path, file))
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove test files
        if os.path.exists(self.test_storage_path):
            for file in os.listdir(self.test_storage_path):
                os.remove(os.path.join(self.test_storage_path, file))
    
    def test_store_memory(self):
        """Test storing a memory."""
        # Run the async test
        result = asyncio.run(self._test_store_memory_async())
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["user_id"], "1")
        self.assertEqual(result["key"], "test_key")
        
        # Verify file was created
        user_file = os.path.join(self.test_storage_path, "user_1.json")
        self.assertTrue(os.path.exists(user_file))
        
        # Verify file content
        with open(user_file, 'r') as f:
            data = json.load(f)
            self.assertEqual(data["test_key"], "test_value")
    
    async def _test_store_memory_async(self):
        """Async implementation of test_store_memory."""
        return await self.memory_service.store_memory("1", "test_key", "test_value")
    
    def test_retrieve_memory(self):
        """Test retrieving a memory."""
        # Run the async test
        result = asyncio.run(self._test_retrieve_memory_async())
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["user_id"], "1")
        self.assertEqual(result["key"], "test_key")
        self.assertEqual(result["value"], "test_value")
    
    async def _test_retrieve_memory_async(self):
        """Async implementation of test_retrieve_memory."""
        # Store a memory first
        await self.memory_service.store_memory("1", "test_key", "test_value")
        
        # Retrieve the memory
        return await self.memory_service.retrieve_memory("1", "test_key")
    
    def test_delete_memory(self):
        """Test deleting a memory."""
        # Run the async test
        result = asyncio.run(self._test_delete_memory_async())
        
        # Verify result
        self.assertTrue(result["success"])
        
        # Verify memory was deleted
        user_file = os.path.join(self.test_storage_path, "user_1.json")
        with open(user_file, 'r') as f:
            data = json.load(f)
            self.assertNotIn("test_key", data)
    
    async def _test_delete_memory_async(self):
        """Async implementation of test_delete_memory."""
        # Store a memory first
        await self.memory_service.store_memory("1", "test_key", "test_value")
        
        # Delete the memory
        return await self.memory_service.delete_memory("1", "test_key")
    
    def test_list_memories(self):
        """Test listing memories."""
        # Run the async test
        result = asyncio.run(self._test_list_memories_async())
        
        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["user_id"], "1")
        self.assertIn("test_key1", result["keys"])
        self.assertIn("test_key2", result["keys"])
        self.assertEqual(len(result["keys"]), 2)
    
    async def _test_list_memories_async(self):
        """Async implementation of test_list_memories."""
        # Store multiple memories
        await self.memory_service.store_memory("1", "test_key1", "test_value1")
        await self.memory_service.store_memory("1", "test_key2", "test_value2")
        
        # List the memories
        return await self.memory_service.list_memories("1")
    
    def test_nonexistent_user(self):
        """Test retrieving a memory for a nonexistent user."""
        # Run the async test
        result = asyncio.run(self._test_nonexistent_user_async())
        
        # Verify result
        self.assertFalse(result["success"])
        self.assertIn("No memories found for user", result["error"])
    
    async def _test_nonexistent_user_async(self):
        """Async implementation of test_nonexistent_user."""
        # Retrieve a memory for a nonexistent user
        return await self.memory_service.retrieve_memory("nonexistent", "test_key")
    
    def test_nonexistent_key(self):
        """Test retrieving a nonexistent memory key."""
        # Run the async test
        result = asyncio.run(self._test_nonexistent_key_async())
        
        # Verify result
        self.assertFalse(result["success"])
        self.assertIn("Memory key 'nonexistent' not found", result["error"])
    
    async def _test_nonexistent_key_async(self):
        """Async implementation of test_nonexistent_key."""
        # Store a memory first
        await self.memory_service.store_memory("1", "test_key", "test_value")
        
        # Retrieve a nonexistent memory key
        return await self.memory_service.retrieve_memory("1", "nonexistent")

if __name__ == '__main__':
    unittest.main()
