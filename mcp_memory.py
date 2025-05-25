"""
MCP-backed memory module for agentic memory in the shopifybot.
Implements the same interface as SimpleMemoryServer, but communicates with the MCP memory server.
"""
import os
import json
import asyncio
from typing import Any, Optional, List
from agents.mcp.server import MCPServerStdio
from embedding_service import EmbeddingService
from vector_store import VectorStore
from mcp.client.stdio import StdioServerParameters
import logging
from typing import Any, Optional
from mcp.types import CallToolResult, TextContent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def naive_linechunk(content: str, max_lines: int = 25) -> List[str]:
    """Split content into chunks of at most max_lines lines each.
    
    This is a simple chunking strategy that splits content based on line count
    without considering semantic boundaries or token limits.
    
    Args:
        content: The text content to chunk
        max_lines: Maximum number of lines per chunk
        
    Returns:
        A list of content chunks
    """
    lines = content.splitlines()
    chunks = []
    
    for i in range(0, len(lines), max_lines):
        chunk = '\n'.join(lines[i:i + max_lines])
        if chunk.strip():  # Only add non-empty chunks
            chunks.append(chunk)
            
    return chunks

# Load MCP memory server config from thinking.json if present
THINKING_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'thinking.json')
DEFAULT_MEMORY_PARAMS = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-memory"],
    "env": {**os.environ.copy(), "MEMORY_FILE_PATH": os.path.join(os.getcwd(), "storage", "memory.json")}
}

if os.path.exists(THINKING_CONFIG_PATH):
    with open(THINKING_CONFIG_PATH, 'r') as f:
        thinking_cfg = json.load(f)
    memory_cfg = thinking_cfg.get("mcpServers", {}).get("memory", {})
    MEMORY_PARAMS = {
        "command": memory_cfg.get("command", DEFAULT_MEMORY_PARAMS["command"]),
        "args": memory_cfg.get("args", DEFAULT_MEMORY_PARAMS["args"]),
        "env": memory_cfg.get("env", DEFAULT_MEMORY_PARAMS["env"])
    }
else:
    MEMORY_PARAMS = DEFAULT_MEMORY_PARAMS


class MCPMemoryServer:
    """
    An MCP-backed implementation of the memory server interface.
    Communicates with the MCP memory server over stdio using MCPServerStdio.
    """
    def __init__(self):
        self.params = MEMORY_PARAMS
        self.cache = True  # Enable tool list caching (optional, matches other servers)
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStore()

        # Schedule the vector store population to run in the background
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._populate_vector_store_on_startup())
            logger.info("MCPMemoryServer __init__: Scheduled vector store population from MCP graph.")
        except RuntimeError:
            logger.warning("MCPMemoryServer __init__: No running event loop, _populate_vector_store_on_startup will not be scheduled. This is expected in some test environments or if not run with an async runner like Uvicorn.")

    async def store_user_memory(self, user_id: str, key: str, value: str):
        user_id = str(user_id)
        """
        Store a memory for a specific user using the knowledge graph MCP server (add_observations).
        Each memory is stored as an observation on the user entity, with the observation content as a dict {"key": ..., "value": ...}.
        """
        # Ensure the user entity exists before adding an observation
        await self._ensure_user_entity_exists(user_id)

        # The 'value' parameter is type-hinted as str and should be a string
        # due to processing in memory_service.store_memory.
        observation_dict = {"key": key, "value": value}
        try:
            # Serialize the dictionary to a JSON string
            observation_json_string = json.dumps(observation_dict)
        except TypeError as e:
            # This is a fallback if 'value' was unexpectedly not a simple string
            logger.error(f"MCP_MEMORY_ERROR: Failed to serialize observation_dict. Key: {key}, Value type: {type(value)}, Error: {e}. Attempting fallback serialization of value.")
            try:
                observation_dict_fallback = {"key": key, "value": str(value) } # Force value to string
                observation_json_string = json.dumps(observation_dict_fallback)
            except Exception as final_e:
                logger.error(f"MCP_MEMORY_CRITICAL: Fallback serialization also failed for key {key}. Error: {final_e}")
                # If even this fails, we might have to raise or return an error to prevent sending malformed data
                return {"success": False, "error": f"Critical error serializing memory for key {key}: {final_e}"}

        args = {
            "observations": [
                {
                    "entityName": user_id,
                    "contents": [observation_json_string]  # 'contents' is now an array of JSON strings
                }
            ]
        }
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=60.0) as server:
            try:
                result = await server.call_tool("add_observations", args)
                # Convert to dict if needed
                processed_result_dict = {}
                if hasattr(result, "to_dict"):
                    processed_result_dict = result.to_dict()
                elif hasattr(result, "__dict__"):
                    processed_result_dict = vars(result)
                elif isinstance(result, dict):
                    processed_result_dict = result # Already a dict
                else:
                    logger.warning(f"MCP_MEMORY_STORE: Unexpected result type from call_tool: {type(result)}. Attempting to return as is.")
                    return result # May or may not be serializable

                # Ensure the 'content' field is JSON serializable
                if "content" in processed_result_dict and isinstance(processed_result_dict["content"], list):
                    serializable_content_list = []
                    for item in processed_result_dict["content"]:
                        if hasattr(item, "text") and isinstance(item.text, str): # Handle TextContent-like objects
                            serializable_content_list.append(item.text)
                        elif isinstance(item, (str, int, float, bool, dict, list)) or item is None: # Already serializable
                            serializable_content_list.append(item)
                        else: # Fallback for other non-serializable types within content
                            logger.warning(f"MCP_MEMORY_STORE: Non-serializable item in content list: {type(item)}. Converting to string.")
                            serializable_content_list.append(str(item))
                    processed_result_dict["content"] = serializable_content_list
                elif "content" in processed_result_dict and hasattr(processed_result_dict["content"], "text") and isinstance(processed_result_dict["content"].text, str):
                    # Handle cases where content might be a single TextContent-like object, not a list
                    logger.debug(f"MCP_MEMORY_STORE: 'content' field is a single TextContent-like object. Extracting text.")
                    processed_result_dict["content"] = processed_result_dict["content"].text
                
                # Also add to the local vector store for proactive retrieval
                try:
                    # First, generate the embedding for the memory's value
                    embedding = self.embedding_service.get_embedding(value) # This is a synchronous call
                    if embedding:
                        # VectorStore.add_embedding is synchronous, so no await needed if it's not an async def
                        # Assuming VectorStore.add_embedding is synchronous based on typical vector store client libraries
                        # If VectorStore.add_embedding IS async, it should be 'await self.vector_store.add_embedding(...)'
                        self.vector_store.add_embedding(user_id, key, embedding)
                        logger.info(f"MCP_MEMORY_STORE: Successfully added embedding for memory key '{key}' for user '{user_id}' to vector store.")
                    else:
                        logger.error(f"MCP_MEMORY_STORE: Failed to generate embedding for key '{key}', user '{user_id}'. Not adding to vector store.")
                except Exception as vs_e:
                    logger.error(f"MCP_MEMORY_STORE: Error during vector store operation for key '{key}', user '{user_id}': {vs_e}")
                    # Decide if this should make the whole operation fail or just be a warning.
                    # For now, let's assume storing in MCP is primary, so we don't alter the return dict here.
            
                return processed_result_dict
            except Exception as e:
                logger.error(f"Failed to add observation via MCPServerStdio: {e}")
                return {"success": False, "error": str(e)}

    async def _ensure_user_entity_exists(self, user_id: str):
        user_id = str(user_id)
        """
        Ensure the user entity exists in the MCP knowledge graph before adding observations.
        """
        args = {
            "entities": [
                {
                    "entityType": "user",
                    "name": user_id,
                    "observations": []
                }
            ]
        }
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            try:
                await server.call_tool("create_entities", args)
            except Exception as e:
                if "already exists" in str(e) or "Entity with name" in str(e):
                    # Entity already exists or similar benign error
                    return
                logger.error(f"Failed to create user entity in MCP: {e}")
                raise

    async def get_user_memory(self, user_id: str, key: str):
        user_id = str(user_id)
        """
        Retrieve a memory for a specific user using the knowledge graph MCP server (open_nodes).
        """
        args = {"names": [user_id]}
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            try:
                result = await server.call_tool("open_nodes", args)
                # Convert to dict if needed
                if hasattr(result, "to_dict"):
                    result = result.to_dict()
                elif hasattr(result, "__dict__"):
                    result = vars(result)
            
                observations = [] # Initialize observations earlier
                # Unwrap and parse the content as JSON
                if "content" in result and isinstance(result["content"], list) and result["content"]:
                    text_content = result["content"][0]
                    if hasattr(text_content, "text"):
                        text = text_content.text
                    elif isinstance(text_content, dict) and "text" in text_content:
                        text = text_content["text"]
                    else:
                        text = None
                    if text:
                        try:
                            parsed = json.loads(text)
                            entities = parsed.get("entities", [])
                            for entity in entities:
                                if entity.get("name") == user_id:
                                    raw_observations = entity.get("observations", [])
                                    # Process observations: parse if string, keep if dict
                                    # observations = [] # Already initialized
                                    for obs_item in raw_observations:
                                        if isinstance(obs_item, str):
                                            try:
                                                parsed_obs = json.loads(obs_item)
                                                observations.append(parsed_obs)
                                            except json.JSONDecodeError as jde:
                                                logger.warning(f"MCP_MEMORY_GET: Failed to JSON decode observation string: '{obs_item}'. Error: {jde}. Skipping this observation.")
                                        elif isinstance(obs_item, dict):
                                            observations.append(obs_item)
                                        else:
                                            logger.warning(f"MCP_MEMORY_GET: Encountered an observation of unexpected type {type(obs_item)}. Value: {obs_item}. Skipping.")
                        except Exception as e:
                            logger.error(f"MCP_MEMORY_GET: Error processing open_nodes result: {e}")
                            return {"success": False, "error": f"Failed to parse open_nodes result: {e}"}
                
                # Find the specific observation by key from the processed list
                target_obs_value = None
                for obs in observations: # Iterate over the processed list
                    if isinstance(obs, dict) and obs.get("key") == key:
                        target_obs_value = obs.get("value")
                        break
                
                if target_obs_value is not None:
                    return {"success": True, "key": key, "value": target_obs_value}
                else:
                    return {"success": False, "error": f"Key '{key}' not found for user '{user_id}'"}
            except Exception as e:
                logger.error(f"MCP_MEMORY_GET: Failed to get memory via MCPServerStdio: {e}")
                return {"success": False, "error": str(e)}

    async def delete_user_memory(self, user_id: str, key: str):
        user_id = str(user_id)
        """
        Delete a memory for a specific user using the knowledge graph MCP server (delete_observations).
        """
        # To delete, we need to find the exact observation content for the key.
        # First, get all observations for the user.
        args_open = {"names": [user_id]}
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            try:
                result_open = await server.call_tool("open_nodes", args_open)
                if hasattr(result_open, "to_dict"):
                    result_open = result_open.to_dict()
                elif hasattr(result_open, "__dict__"):
                    result_open = vars(result_open)

                parsed_observations_dicts = []
                if "content" in result_open and isinstance(result_open["content"], list) and result_open["content"]:
                    text_content_outer = result_open["content"][0]
                    text_data = None
                    if hasattr(text_content_outer, "text"):
                        text_data = text_content_outer.text
                    elif isinstance(text_content_outer, dict) and "text" in text_content_outer:
                        text_data = text_content_outer["text"]

                    if text_data:
                        try:
                            parsed_json = json.loads(text_data)
                            entities = parsed_json.get("entities", [])
                            for entity in entities:
                                if entity.get("name") == user_id:
                                    raw_observations = entity.get("observations", [])
                                    for obs_item_str in raw_observations:
                                        if isinstance(obs_item_str, str):
                                            try:
                                                # Observations are stored as JSON strings of dicts like {"key": ..., "value": ...}
                                                parsed_obs_dict = json.loads(obs_item_str)
                                                parsed_observations_dicts.append(parsed_obs_dict)
                                            except json.JSONDecodeError as jde:
                                                logger.warning(f"MCP_MEMORY_DELETE: Failed to JSON decode observation string: '{obs_item_str}'. Error: {jde}. Skipping.")
                                        # If it's already a dict (should not happen if stored as string), log and skip or handle
                                        elif isinstance(obs_item_str, dict):
                                            logger.warning(f"MCP_MEMORY_DELETE: Encountered pre-parsed dict observation: {obs_item_str}. This is unexpected. Adding directly.")
                                            parsed_observations_dicts.append(obs_item_str)
                        except Exception as e:
                            logger.error(f"MCP_MEMORY_DELETE: Error processing open_nodes result: {e}")
                            return {"success": False, "error": f"Failed to parse open_nodes result: {e}"}
                
                # Find the specific observation dictionary that matches the key.
                target_obs_dict_to_delete = None
                for obs_dict in parsed_observations_dicts:
                    if isinstance(obs_dict, dict) and obs_dict.get("key") == key:
                        target_obs_dict_to_delete = obs_dict
                        break
                
                if not target_obs_dict_to_delete:
                    logger.info(f"MCP_MEMORY_DELETE: Key '{key}' not found for user '{user_id}'. No deletion performed.")
                    return {"success": True, "message": f"Key '{key}' not found for user '{user_id}', no deletion performed."}

                # Convert the target observation dictionary back to its original JSON string form for deletion.
                try:
                    observation_string_to_delete = json.dumps(target_obs_dict_to_delete)
                except TypeError as e:
                    logger.error(f"MCP_MEMORY_DELETE: Failed to serialize target observation for deletion. Key: {key}, Obs: {target_obs_dict_to_delete}, Error: {e}")
                    return {"success": False, "error": f"Failed to serialize observation for deletion: {e}"}

                args_delete = {
                    "deletions": [
                        {
                            "entityName": user_id,
                            "observations": [observation_string_to_delete]  # Must be a list of strings
                        }
                    ]
                }
                
                result_del = await server.call_tool("delete_observations", args_delete)
                
                processed_result_dict = {}
                if hasattr(result_del, "to_dict"):
                    processed_result_dict = result_del.to_dict()
                elif hasattr(result_del, "__dict__"):
                    processed_result_dict = vars(result_del)
                elif isinstance(result_del, dict):
                    processed_result_dict = result_del
                else:
                    logger.warning(f"MCP_MEMORY_DELETE: Unexpected result_del type from call_tool: {type(result_del)}. Attempting to return as is.")
                    return result_del # May or may not be serializable

                # Ensure the 'content' field is JSON serializable if present
                if "content" in processed_result_dict:
                    content_val = processed_result_dict["content"]
                    if isinstance(content_val, list):
                        serializable_content_list = []
                        for item in content_val:
                            if hasattr(item, "text") and isinstance(item.text, str):
                                serializable_content_list.append(item.text)
                            elif isinstance(item, (str, int, float, bool, dict, list)) or item is None:
                                serializable_content_list.append(item)
                            else:
                                logger.warning(f"MCP_MEMORY_DELETE: Non-serializable item in content list: {type(item)}. Converting to string.")
                                serializable_content_list.append(str(item))
                        processed_result_dict["content"] = serializable_content_list
                    elif hasattr(content_val, "text") and isinstance(content_val.text, str):
                        processed_result_dict["content"] = content_val.text
                    # If content is already a serializable type, leave it as is.
                
                # Add success field if not present, assuming MCP tool implies success if no error
                if "success" not in processed_result_dict:
                    processed_result_dict["success"] = True

                # Whether MCP deletion was successful or observation wasn't found, attempt to delete from local vector store for consistency
                try:
                    delete_vec_success = self.vector_store.delete_embedding(user_id, key)
                    if delete_vec_success:
                        logger.info(f"[MCP_MEMORY_VECTOR] Deleted embedding for user {user_id}, key {key} from local vector store.")
                    else:
                        logger.info(f"[MCP_MEMORY_VECTOR] Embedding for user {user_id}, key {key} not found in local vector store or failed to delete.")
                except Exception as e_vec_delete:
                    logger.error(f"[MCP_MEMORY_VECTOR] Error deleting embedding for user {user_id}, key {key} from local vector store: {e_vec_delete}", exc_info=True)
                
                return processed_result_dict

            except Exception as e:
                logger.error(f"MCP_MEMORY_DELETE: Overall failure in delete_user_memory for key '{key}', user '{user_id}': {e}")
                return {"success": False, "error": str(e)}

    async def list_user_memories(self, user_id: str):
        user_id = str(user_id)
        """
        List all memory keys for a specific user using the knowledge graph MCP server (open_nodes).
        """
        args = {"names": [user_id]}
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            try:
                result = await server.call_tool("open_nodes", args)
                # Convert to dict if needed
                if hasattr(result, "to_dict"):
                    result = result.to_dict()
                elif hasattr(result, "__dict__"):
                    result = vars(result)
                # Unwrap and parse the content as JSON
                observations = []
                if "content" in result and isinstance(result["content"], list) and result["content"]:
                    text_content = result["content"][0]
                    if hasattr(text_content, "text"):
                        text = text_content.text
                    elif isinstance(text_content, dict) and "text" in text_content:
                        text = text_content["text"]
                    else:
                        text = None
                    if text:
                        try:
                            parsed = json.loads(text)
                            entities = parsed.get("entities", [])
                            for entity in entities:
                                if entity.get("name") == user_id:
                                    raw_observations = entity.get("observations", [])
                                    # Process observations: parse if string, keep if dict
                                    observations = [] # This will store the processed (parsed) observations
                                    for obs_item in raw_observations:
                                        if isinstance(obs_item, str):
                                            try:
                                                parsed_obs = json.loads(obs_item)
                                                observations.append(parsed_obs)
                                            except json.JSONDecodeError as jde:
                                                logger.warning(f"MCP_MEMORY_LIST: Failed to JSON decode observation string: '{obs_item}'. Error: {jde}. Skipping this observation.")
                                        elif isinstance(obs_item, dict):
                                            observations.append(obs_item)
                                        else:
                                            logger.warning(f"MCP_MEMORY_LIST: Encountered an observation of unexpected type {type(obs_item)}. Value: {obs_item}. Skipping.")
                        except Exception as e:
                            logger.error(f"MCP_MEMORY_LIST: Error processing open_nodes result: {e}")
                            return {"success": False, "keys": [], "count": 0, "error": f"Failed to parse open_nodes result: {e}"}
                keys = [obs.get("key") for obs in observations if isinstance(obs, dict) and "key" in obs]
                return {"success": True, "keys": keys, "count": len(keys)}
            except Exception as e:
                logger.error(f"Failed to list memories via MCPServerStdio: {e}")
                return {"success": False, "keys": [], "count": 0, "error": str(e)}

    async def proactively_retrieve_memories(self, user_id: str, query_text: str, top_n: int = 5):
        user_id = str(user_id)
        """
        Proactively retrieves memories relevant to a query_text using vector similarity.
        """
        logger.info(f"[MCP_MEMORY_PROACTIVE] Attempting to retrieve memories for user {user_id} (top_n={top_n}) based on query: '{query_text[:50]}...'" )
        retrieved_memories_content = []
        try:
            query_embedding = self.embedding_service.get_embedding(query_text)
            if not query_embedding:
                logger.warning(f"[MCP_MEMORY_PROACTIVE] Could not generate embedding for query: '{query_text[:50]}...'. Skipping retrieval.")
                return []

            # Find similar memory keys from the vector store
            similar_memory_keys = self.vector_store.find_similar_embeddings(user_id, query_embedding, top_n=top_n)
            
            if not similar_memory_keys:
                logger.info(f"[MCP_MEMORY_PROACTIVE] No similar memory keys found for user {user_id} and query.")
                return []

            logger.info(f"[MCP_MEMORY_PROACTIVE] Found {len(similar_memory_keys)} similar memory keys: {similar_memory_keys}")

            # Retrieve the actual content of these memories
            for key_string, _score in similar_memory_keys: # Unpack tuple
                memory_data = await self.get_user_memory(user_id, key_string) # Pass the string key
                if memory_data and memory_data.get("success") and "value" in memory_data:
                    content_value = memory_data["value"]
                    retrieved_memories_content.append(content_value)
                    logger.debug(f"[MCP_MEMORY_PROACTIVE] Appended content for key '{key_string}': '{str(content_value)[:70]}...'" )
                elif memory_data and not memory_data.get("success"):
                    logger.warning(f"[MCP_MEMORY_PROACTIVE] Failed to retrieve content for memory key {key_string}: {memory_data.get('error', 'Unknown error')}")
                else:
                    logger.warning(f"[MCP_MEMORY_PROACTIVE] No content found or unexpected structure for memory key {key_string}.")
        
            logger.info(f"[MCP_MEMORY_PROACTIVE] Successfully retrieved content for {len(retrieved_memories_content)} memories.")
            return retrieved_memories_content

        except Exception as e:
            logger.error(f"[MCP_MEMORY_PROACTIVE] Error during proactive memory retrieval for user {user_id}: {e}", exc_info=True)
            return [] # Return empty list on error

    async def _populate_vector_store_on_startup(self):
        """Populates the VectorStore by reading all data from the live MCP memory server via read_graph."""
        logger.info("MCP_POPULATE: Starting vector store pre-population using MCP read_graph.")
        
        total_memories_processed = 0
        total_memories_embedded = 0

        try:
            logger.info("MCP_POPULATE: Creating MCPServerStdio instance to call read_graph.")
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                logger.info("MCP_POPULATE: Calling read_graph tool via MCPServerStdio instance.")
                graph_data_response = await server.call_tool("read_graph", {})         
            
            if not graph_data_response:
                logger.error("MCP_POPULATE: Received no response or None from read_graph.")
                return

            logger.debug(f"MCP_POPULATE: Raw response from read_graph: {type(graph_data_response)}, {str(graph_data_response)[:500]}")

            actual_graph_data_dict = None
            if isinstance(graph_data_response, CallToolResult):
                if (graph_data_response.content and 
                    len(graph_data_response.content) > 0 and 
                    isinstance(graph_data_response.content[0], TextContent)):
                    json_text = graph_data_response.content[0].text
                    try:
                        actual_graph_data_dict = json.loads(json_text)
                        logger.debug(f"MCP_POPULATE: Successfully parsed JSON from TextContent: {str(actual_graph_data_dict)[:500]}")
                    except json.JSONDecodeError as e:
                        logger.error(f"MCP_POPULATE: Failed to parse JSON from read_graph TextContent: {e}. JSON: {json_text[:500]}")
                        return
                else:
                    logger.error(f"MCP_POPULATE: read_graph CallToolResult content is not as expected or empty. Content: {graph_data_response.content}")
                    return
            elif isinstance(graph_data_response, dict): # Fallback, less likely now
                actual_graph_data_dict = graph_data_response
                logger.debug(f"MCP_POPULATE: graph_data_response was already a dict: {str(actual_graph_data_dict)[:500]}")
            else:
                logger.error(f"MCP_POPULATE: graph_data_response is not a CallToolResult or dict. Type: {type(graph_data_response)}")
                return

            if not actual_graph_data_dict:
                 logger.error("MCP_POPULATE: Could not derive actual graph data dictionary from response.")
                 return
            
            entities_list = actual_graph_data_dict.get("entities")

            if not isinstance(entities_list, list):
                logger.info(f"MCP_POPULATE: 'entities' field is not a list or not found in parsed data. Parsed data: {str(actual_graph_data_dict)[:500]}")
                entities_list = [] 
            
            if not entities_list:
                logger.info(f"MCP_POPULATE: No entities found in the graph data list.")
            else:
                logger.info(f"MCP_POPULATE: Found {len(entities_list)} entities in the MCP graph list.")
                for entity_data_dict in entities_list:
                    if not isinstance(entity_data_dict, dict):
                        logger.warning(f"MCP_POPULATE: Entity data item is not a dictionary. Skipping. Data: {entity_data_dict}")
                        continue
                    
                    user_id = entity_data_dict.get("name")
                    entity_type = entity_data_dict.get("entityType")

                    if not user_id or entity_type != "user": # Ensure it's a user entity
                        logger.warning(f"MCP_POPULATE: Skipping entity with missing name or non-user type. Name: {user_id}, Type: {entity_type}")
                        continue
                    
                    observations = entity_data_dict.get("observations", [])
                    if not isinstance(observations, list): # Observations should be a list
                        logger.warning(f"MCP_POPULATE: Observations for user '{user_id}' is not a list. Skipping. Observations: {observations}")
                        continue

                    if not observations:
                        logger.info(f"MCP_POPULATE: No observations (memories) found for user_id: {user_id}.")
                        continue
                    
                    logger.info(f"MCP_POPULATE: Processing {len(observations)} observations for user_id: {user_id}.")
                    for obs_item in observations:  # Renamed to generic obs_item
                        total_memories_processed += 1
                        memory_dict_parsed = None
                        
                        if isinstance(obs_item, str):
                            try:
                                memory_dict_parsed = json.loads(obs_item)
                            except json.JSONDecodeError as jde:
                                logger.error(f"MCP_POPULATE: Failed to parse observation JSON string for user '{user_id}'. Error: {jde}. Observation string: '{obs_item}'")
                                continue # Skip this malformed observation
                        elif isinstance(obs_item, dict):
                            memory_dict_parsed = obs_item # It's already a dictionary
                        else:
                            logger.warning(f"MCP_POPULATE: Observation for user '{user_id}' is neither a string nor a dict. Type: {type(obs_item)}, Value: {str(obs_item)[:100]}. Skipping.")
                            continue
                        
                        # Now memory_dict_parsed should be a dictionary
                        key = memory_dict_parsed.get("key")
                        value = memory_dict_parsed.get("value")

                        if key is None or value is None:
                            logger.warning(f"MCP_POPULATE: Parsed observation for user '{user_id}' is missing key or value. Parsed dict: {memory_dict_parsed}")
                            continue
                        
                        embedding_value_str = str(value) # Ensure value is string for embedding
                        embedding = self.embedding_service.get_embedding(embedding_value_str)
                        if embedding:
                            self.vector_store.add_embedding(user_id, key, embedding)
                            total_memories_embedded += 1
                            logger.debug(f"MCP_POPULATE: Successfully pre-populated embedding for user '{user_id}', key '{key}'.")
                        else:
                            logger.warning(f"MCP_POPULATE: Failed to generate embedding for user '{user_id}', key '{key}' (value: '{embedding_value_str[:50]}...').")
        
        except AttributeError as ae: # Catch attribute errors specifically if they still occur
            logger.error(f"MCP_POPULATE: AttributeError during pre-population: {ae}. This might indicate an unexpected object structure.", exc_info=True)
        except Exception as e:
            logger.error(f"MCP_POPULATE: An unexpected error occurred during the pre-population process: {e}", exc_info=True)
        
        logger.info(f"MCP_POPULATE: VectorStore pre-population via read_graph attempt complete. Processed: {total_memories_processed}, Embedded: {total_memories_embedded}.")

_mcp_memory_server_instance: Optional[MCPMemoryServer] = None

def get_mcp_memory_server() -> MCPMemoryServer:
    """Returns a singleton instance of MCPMemoryServer."""
    global _mcp_memory_server_instance
    if _mcp_memory_server_instance is None:
        logger.info("Creating new MCPMemoryServer instance.")
        _mcp_memory_server_instance = MCPMemoryServer()
    return _mcp_memory_server_instance
