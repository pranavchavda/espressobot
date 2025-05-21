import asyncio
import os
from mcp_memory import MCPMemoryServer
memory_server = MCPMemoryServer()
# import pytest


# @pytest.mark.asyncio


import json

def parse_mcp_observations(open_nodes_result, user_id):
    if "content" in open_nodes_result and isinstance(open_nodes_result["content"], list) and open_nodes_result["content"]:
        text_content = open_nodes_result["content"][0]
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
                        return entity.get("observations", [])
            except Exception as e:
                print(f"[DEBUG] Failed to parse open_nodes content: {e}")
    return []

def get_memory_from_observations(observations, key):
    for obs in observations:
        if obs.get("key") == key:
            return obs.get("value")
    return None

def list_memory_keys(observations):
    return [obs.get("key") for obs in observations if "key" in obs]

async def test_memory():
    user_id = "best_user"
    key = "favorite_color"
    value = "blue"

    print(f"Storing memory: user_id={user_id}, key={key}, value={value}")
    store_result = await memory_server.store_user_memory(str(user_id), key, value)
    print("Store result:", store_result)

    # --- MCP DEBUG: Immediately call open_nodes and print the raw structure
    try:
        from agents.mcp.server import MCPServerStdio
        from mcp_memory import MEMORY_PARAMS
        async with MCPServerStdio(params=MEMORY_PARAMS, cache_tools_list=True) as server:
            open_nodes_result = await server.call_tool("open_nodes", {"names": [str(user_id)]})
            if hasattr(open_nodes_result, "to_dict"):
                open_nodes_result = open_nodes_result.to_dict()
            elif hasattr(open_nodes_result, "__dict__"):
                open_nodes_result = vars(open_nodes_result)
            print(f"[DEBUG] open_nodes result after store: {open_nodes_result}")
            # --- Unified parsing for all operations ---
            observations = parse_mcp_observations(open_nodes_result, str(user_id))
            print(f"[DEBUG] Parsed observations for {user_id}: {observations}")
            # Simulate get
            found_value = get_memory_from_observations(observations, key)
            print(f"[DEBUG] [GET] Value for key '{key}': {found_value}")
            # Simulate list
            keys = list_memory_keys(observations)
            print(f"[DEBUG] [LIST] Keys for {user_id}: {keys}")
            # Simulate delete
            to_delete = [obs for obs in observations if obs.get("key") == key]
            print(f"[DEBUG] [DELETE] Would delete: {to_delete}")
    except Exception as e:
        print(f"[DEBUG] Error calling open_nodes for debug: {e}")

    print(f"Retrieving memory: user_id={user_id}, key={key}")
    # Try both MCP and SimpleMemory interface compatibility
    if hasattr(memory_server, 'get_user_memory'):
        retrieved = await memory_server.get_user_memory(str(user_id), key)
        print("Retrieved value:", retrieved)
    else:
        retrieved = await memory_server.retrieve_user_memory(str(user_id), key)
        print("Retrieved value:", retrieved)

    print(f"Deleting memory: user_id={user_id}, key={key}")
    delete_result = await memory_server.delete_user_memory(str(user_id), key)
    print("Delete result:", delete_result)

    print(f"Retrieving memory after deletion: user_id={user_id}, key={key}")
    if hasattr(memory_server, 'get_user_memory'):
        retrieved_after = await memory_server.get_user_memory(str(user_id), key)
        print("Retrieved after delete:", retrieved_after)
    else:
        retrieved_after = await memory_server.retrieve_user_memory(str(user_id), key)
        print("Retrieved after delete:", retrieved_after)

if __name__ == "__main__":
    asyncio.run(test_memory())

    # --- Test parsing logic with a hardcoded MCP open_nodes result ---
    print("\n[TEST] Parsing hardcoded MCP open_nodes result...")
    sample_result = {
        'meta': None,
        'content': [
            {'type': 'text', 'text': '{\n  "entities": [\n    {\n      "type": "entity",\n      "entityType": "user",\n      "name": "test_user",\n      "observations": [\n        {\n          "key": "favorite_color",\n          "value": "blue"\n        },\n        {\n          "key": "favorite_color",\n          "value": "blue"\n        }\n      ]\n    }\n  ],\n  "relations": []\n}', 'annotations': None}
        ],
        'isError': False
    }
    user_id = "test_user"
    key = "favorite_color"
    if "content" in sample_result and isinstance(sample_result["content"], list) and sample_result["content"]:
        text_content = sample_result["content"][0]
        if hasattr(text_content, "text"):
            text = text_content.text
        elif isinstance(text_content, dict) and "text" in text_content:
            text = text_content["text"]
        else:
            text = None
        if text:
            try:
                import json
                parsed = json.loads(text)
                entities = parsed.get("entities", [])
                for entity in entities:
                    if entity.get("name") == user_id:
                        observations = entity.get("observations", [])
                        print(f"[TEST] Parsed observations for {user_id}: {observations}")
                        for obs in observations:
                            if obs.get("key") == key:
                                print(f"[TEST] Found value for key '{key}': {obs.get('value')}")
            except Exception as e:
                print(f"[TEST] Failed to parse open_nodes content: {e}")
