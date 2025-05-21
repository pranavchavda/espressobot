"""
MCP-backed memory module for agentic memory in the shopifybot.
Implements the same interface as SimpleMemoryServer, but communicates with the MCP memory server.
"""
import os
import json
import os
from typing import Any, Optional
from agents.mcp.server import MCPServerStdio
from mcp.client.stdio import StdioServerParameters
import logging
from typing import Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
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
                                    observations = []
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
        # To delete, we need to find the exact observation content for the key
        args_open = {"names": [user_id]}
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            try:
                result = await server.call_tool("open_nodes", args_open)
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
                                                logger.warning(f"MCP_MEMORY_DELETE: Failed to JSON decode observation string: '{obs_item}'. Error: {jde}. Skipping this observation.")
                                        elif isinstance(obs_item, dict):
                                            observations.append(obs_item)
                                        else:
                                            logger.warning(f"MCP_MEMORY_DELETE: Encountered an observation of unexpected type {type(obs_item)}. Value: {obs_item}. Skipping.")
                        except Exception as e:
                            logger.error(f"MCP_MEMORY_DELETE: Error processing open_nodes result: {e}")
                            return {"success": False, "error": f"Failed to parse open_nodes result: {e}"}
                target_obs = [obs for obs in observations if isinstance(obs, dict) and obs.get("key") == key]
                if not target_obs:
                    return {"success": False, "error": f"Key '{key}' not found for user '{user_id}'"}
                args_delete = {
                    "deletions": [
                        {
                            "entityName": user_id,
                            "observations": target_obs
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
                    processed_result_dict = result_del # Already a dict
                else:
                    logger.warning(f"MCP_MEMORY_DELETE: Unexpected result_del type from call_tool: {type(result_del)}. Attempting to return as is.")
                    return result_del # May or may not be serializable

                # Ensure the 'content' field is JSON serializable
                if "content" in processed_result_dict and isinstance(processed_result_dict["content"], list):
                    serializable_content_list = []
                    for item in processed_result_dict["content"]:
                        if hasattr(item, "text") and isinstance(item.text, str): # Handle TextContent-like objects
                            serializable_content_list.append(item.text)
                        elif isinstance(item, (str, int, float, bool, dict, list)) or item is None: # Already serializable
                            serializable_content_list.append(item)
                        else: # Fallback for other non-serializable types within content
                            logger.warning(f"MCP_MEMORY_DELETE: Non-serializable item in content list: {type(item)}. Converting to string.")
                            serializable_content_list.append(str(item))
                    processed_result_dict["content"] = serializable_content_list
                elif "content" in processed_result_dict and hasattr(processed_result_dict["content"], "text") and isinstance(processed_result_dict["content"].text, str):
                    # Handle cases where content might be a single TextContent-like object, not a list
                    logger.debug(f"MCP_MEMORY_DELETE: 'content' field is a single TextContent-like object. Extracting text.")
                    processed_result_dict["content"] = processed_result_dict["content"].text
                
                return processed_result_dict
            except Exception as e:
                logger.error(f"Failed to delete observation via MCPServerStdio: {e}")
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
