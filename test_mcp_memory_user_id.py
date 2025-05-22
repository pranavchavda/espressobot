import unittest
from unittest.mock import patch, AsyncMock, ANY, call, MagicMock
import asyncio
import json
import logging
from mcp_memory import MCPMemoryServer
from vector_store import VectorStore # Assuming VectorStore is the class in vector_store.py
from embedding_service import EmbeddingService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@patch('mcp_memory.MCPServerStdio')  # Patching where it's used in mcp_memory module
class TestMCPMemoryUserId(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Basic setup that doesn't depend on the class-level mock directly
        self.memory_server = MCPMemoryServer()
        self.memory_server.embedding_service = AsyncMock(spec=EmbeddingService)
        self.memory_server.embedding_service.get_embedding.return_value = [0.1] * 10 # Dummy embedding
        self.memory_server.vector_store = AsyncMock(spec=VectorStore)
        self.memory_server.vector_store.add_document = AsyncMock() # For the manual call in the test

    async def test_store_and_retrieve_with_string_user_id(self, MockMCPServerStdio_class): # Mock passed by class decorator
        # MockMCPServerStdio_class is the patched class, an AsyncMock itself, passed by the decorator.

        # This is the single mock instance for the call_tool method. All calls should be routed here.
        self.mock_call_tool_method = AsyncMock(name="mock_call_tool_method_SINGLETON")

        # This is the single mock for the server instance that MCPServerStdio's context manager will yield.
        # Its .call_tool attribute is set to our single mock_call_tool_method.
        self.mock_stdio_server_instance = AsyncMock(name="mock_stdio_server_instance_SINGLETON")
        print(f"[TEST_DEBUG] Created self.mock_stdio_server_instance: {id(self.mock_stdio_server_instance)}")
        self.mock_stdio_server_instance.call_tool = self.mock_call_tool_method
        print(f"[TEST_DEBUG] Assigned self.mock_call_tool_method ({id(self.mock_call_tool_method)}) to self.mock_stdio_server_instance.call_tool")

        # This factory function will be called every time MCPServerStdio() is instantiated in the code under test.
        # It returns a new, distinct mock context manager each time.
        def create_mock_context_manager(*args, **kwargs):
            print(f"[TEST_DEBUG] create_mock_context_manager called (MCPServerStdio() instantiated). Call count: {MockMCPServerStdio_class.call_count}")
            context_manager_mock = AsyncMock(name=f"context_manager_for_call_{MockMCPServerStdio_class.call_count}")
            print(f"[TEST_DEBUG]   Created context_manager_mock: {id(context_manager_mock)}")
            context_manager_mock.__aenter__.return_value = self.mock_stdio_server_instance
            print(f"[TEST_DEBUG]   Set context_manager_mock.__aenter__ to return: {id(self.mock_stdio_server_instance)}")
            context_manager_mock.__aexit__ = AsyncMock(return_value=None)
            return context_manager_mock

        # Configure the patched class (MockMCPServerStdio_class) to use this factory function
        # as its side_effect. This means MCPServerStdio() will execute this function.
        MockMCPServerStdio_class.side_effect = create_mock_context_manager
        print(f"[TEST_DEBUG] Set MockMCPServerStdio_class.side_effect to factory: {id(create_mock_context_manager)}")

        user_id_str = '1'
        memory_key = "mcp_breville_sale_info"
        memory_value = "The Breville espresso machine sale ends next Tuesday."
        query = "When does the MCP Breville sale end?"

        # --- Phase 1: Test store_user_memory ---
        # Mock the response object that call_tool is expected to return.
        # This object should have a to_dict() method.

        # For _ensure_user_entity_exists -> open_nodes
        mock_response_open_nodes_user_check = AsyncMock() # This is what 'await call_tool()' returns
        mock_response_open_nodes_user_check.to_dict = unittest.mock.Mock(return_value={'nodes': []}) # .to_dict() is a sync method

        # For _ensure_user_entity_exists -> create_entities
        mock_response_create_entities_user = AsyncMock()
        mock_response_create_entities_user.to_dict = unittest.mock.Mock(return_value={'success': True, 'entities': [{'name': user_id_str}]})

        # For store_user_memory -> add_observations
        mock_response_add_observations = AsyncMock()
        mock_response_add_observations.to_dict = unittest.mock.Mock(return_value={'success': True, 'message': 'Observations added'})

        # This list will be mutated by the side_effect function and reset by the test phases
        responses_for_call_tool_side_effect = []

        # Define expected call sequence for clarity in the side_effect
        expected_tool_calls_phase1 = ["create_entities", "add_observations"]
        expected_tool_calls_phase2 = ["open_nodes"]

        # This list will be mutated by the side_effect function and reset by the test phases
        responses_for_call_tool_side_effect = []
        current_expected_tool_calls = [] # To track which phase we are in for error messages

        def mock_call_tool_side_effect_func(*args, **kwargs):
            tool_name_called = args[0]
            tool_args_called = args[1]
            call_number = self.mock_call_tool_method.call_count # call_count is 1-based for the current call
            
            print(f"[TEST_DEBUG_SIDE_EFFECT] mock_call_tool_side_effect_func CALLED ({call_number}) for tool: '{tool_name_called}' with args: {tool_args_called}")

            if not responses_for_call_tool_side_effect:
                error_msg = f"[ERROR] Side_effect called for '{tool_name_called}' but no responses left! (Call #{call_number})"
                print(error_msg)
                raise AssertionError(error_msg)

            # Check if the called tool matches the expectation for this position in the sequence
            expected_tool_for_this_call = "<None (ran out of expected sequence)>"
            if call_number <= len(current_expected_tool_calls):
                expected_tool_for_this_call = current_expected_tool_calls[call_number -1]
            
            if tool_name_called != expected_tool_for_this_call:
                print(f"[TEST_WARNING_SIDE_EFFECT]   Tool call mismatch! Expected '{expected_tool_for_this_call}', but got '{tool_name_called}'. (Call #{call_number})")
                # This might be the root of the problem if open_nodes is skipped and create_entities is called first.
            
            response_to_return = responses_for_call_tool_side_effect.pop(0)
            print(f"[TEST_DEBUG_SIDE_EFFECT]   Returning mock (ID: {id(response_to_return)}) for '{tool_name_called}'. Responses left: {len(responses_for_call_tool_side_effect)}.")
            return response_to_return

        print(f"[TEST_DEBUG] Phase 1: Setting side_effect on self.mock_call_tool_method ({id(self.mock_call_tool_method)}) to custom function.")
        current_expected_tool_calls = expected_tool_calls_phase1
        responses_for_call_tool_side_effect.clear()
        # _ensure_user_entity_exists calls create_entities. If successful, it doesn't use the return value.
        # If it fails due to existing entity, it catches the exception.
        # store_user_memory then calls add_observations.
        responses_for_call_tool_side_effect.extend([
            mock_response_create_entities_user,    # For _ensure_user_entity_exists -> create_entities
            mock_response_add_observations         # For store_user_memory -> add_observations
        ])
        self.mock_call_tool_method.side_effect = mock_call_tool_side_effect_func

        logger.info(f"Test (MCP): Storing memory for user_id='{user_id_str}', key='{memory_key}'")
        store_result = await self.memory_server.store_user_memory(user_id_str, memory_key, memory_value)

        self.assertIsNotNone(store_result, "store_user_memory returned None")
        self.assertTrue(store_result.get("success"), f"MCP Failed to store memory: {store_result.get('message')}")

        expected_observation_content = json.dumps({'key': memory_key, 'value': memory_value, 'type': 'explicit'})
        expected_calls_store = [
            call("create_entities", {'entities': [{'entityType': 'user', 'name': user_id_str, 'observations': []}]}), # From _ensure_user_entity_exists
            call("add_observations", {'observations': [{'entityName': user_id_str, 'contents': [ANY]}]}) # From store_user_memory
        ]
        self.assertEqual(self.mock_call_tool_method.call_args_list, expected_calls_store)
        
        # Simulate adding to local vector store as store_user_memory would do after successful MCP store
        await self.memory_server.vector_store.add_document(user_id_str, memory_key, memory_value, self.memory_server.embedding_service.get_embedding.return_value)
        self.memory_server.vector_store.add_document.assert_called_once_with(user_id_str, memory_key, memory_value, self.memory_server.embedding_service.get_embedding.return_value)

        # --- Phase 2: Test proactively_retrieve_memories ---
        self.mock_call_tool_method.reset_mock() # This also clears .side_effect
        self.memory_server.vector_store.find_similar_embeddings.reset_mock()
        self.memory_server.embedding_service.get_embedding.reset_mock()

        # Mock the embedding service and vector store for proactive retrieval
        self.memory_server.embedding_service.get_embedding.return_value = [0.1, 0.2, 0.3] # Dummy embedding
        self.memory_server.vector_store.find_similar_embeddings.return_value = [(memory_key, 0.9)] 

        # For proactively_retrieve_memories -> get_user_memory -> open_nodes
        mock_response_get_memory_proactive = AsyncMock()
        mock_node_data_proactive = {
            'name': user_id_str,
            'entityType': 'user',
            'observations': [json.dumps({"key": memory_key, "value": memory_value, "type": "explicit"})]
        }
        mock_response_get_memory_proactive.to_dict = unittest.mock.Mock(
            return_value={"content": [{"text": json.dumps({"entities": [mock_node_data_proactive]})}]}
        )

        print(f"[TEST_DEBUG] Phase 2: Setting side_effect on self.mock_call_tool_method ({id(self.mock_call_tool_method)}) to custom function.")
        current_expected_tool_calls = expected_tool_calls_phase2
        responses_for_call_tool_side_effect.clear()
        responses_for_call_tool_side_effect.extend([
            mock_response_get_memory_proactive # Corresponds to expected_tool_calls_phase2[0]
        ])
        self.mock_call_tool_method.side_effect = mock_call_tool_side_effect_func # Re-assign after reset_mock

        logger.info(f"Test (MCP): Retrieving memory for user_id='{user_id_str}' with query='{query}'")
        retrieved_memories = await self.memory_server.proactively_retrieve_memories(user_id_str, query)

        self.memory_server.embedding_service.get_embedding.assert_called_with(query)
        self.memory_server.vector_store.find_similar_embeddings.assert_called_once_with(user_id_str, self.memory_server.embedding_service.get_embedding.return_value, top_n=5)
        
        self.mock_call_tool_method.assert_called_once_with('open_nodes', {'names': [user_id_str]})

        self.assertIsNotNone(retrieved_memories, "MCP Proactive retrieval returned None")
        self.assertGreater(len(retrieved_memories), 0, "MCP No memories retrieved proactively")
        # proactively_retrieve_memories returns a list of memory *values*
        self.assertIn(memory_value, retrieved_memories, "Proactively retrieved memory content does not match expected value")

if __name__ == '__main__':
    unittest.main()
