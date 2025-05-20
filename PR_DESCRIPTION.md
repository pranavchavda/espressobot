# MCP Server Integrations

This PR adds integration with four Model Context Protocol (MCP) servers to enhance the Shopify Agent's capabilities:

## 1. Memory MCP Server

Provides user-specific persistent memory storage across conversations:

- **Core Features:**
  - User-specific namespace isolation
  - Persistent storage in database
  - Memory retrieval, listing, and deletion

- **Key Files:**
  - `mcp_server.py`: `MemoryMCPServer` class
  - `memory_service.py`: Memory service for combined in-memory/database storage
  - `models.py`: `UserMemory` database model
  - Added corresponding database migration

- **Agent Tools:**
  - `store_user_memory`
  - `retrieve_user_memory`
  - `list_user_memories`
  - `delete_user_memory`

## 2. Fetch MCP Server

Provides enhanced web content retrieval capabilities:

- **Core Features:**
  - Robust URL fetching with better error handling
  - HTML-to-text conversion for cleaner data
  - CSS selector filtering for targeted content extraction
  - JSON parsing for API responses

- **Key Files:**
  - `mcp_server.py`: `FetchMCPServer` class

- **Agent Tools:**
  - `fetch_and_extract_text`
  - `fetch_json`

## 3. Sequential Thinking MCP Server

Enhances the agent's reasoning process with structured thinking:

- **Core Features:**
  - Formal step-by-step reasoning
  - Specialized problem-solving framework
  - Code planning capabilities
  - Explicit conclusions based on reasoning steps

- **Key Files:**
  - `mcp_server.py`: `SequentialThinkingMCPServer` class

- **Agent Tools:**
  - `structured_thinking`
  - `solve_problem`
  - `plan_code`

## 4. Filesystem MCP Server

Provides controlled filesystem access for persistent storage:

- **Core Features:**
  - Controlled read/write access to designated directories
  - Organized storage for templates, exports, and user-specific files
  - Path validation and security

- **Key Files:**
  - `mcp_server.py`: `FilesystemMCPServer` class
  - Created storage directory structure (templates, exports, users)

- **Agent Tools:**
  - `read_file`
  - `write_file`
  - `list_directory`
  - `delete_file`
  - `check_file_exists`

## System Prompt Updates

The agent's system prompt has been enhanced with:

- Description of each MCP server's capabilities
- Usage guidance for each tool category
- Examples of good use cases for each capability

## Implementation Notes

1. All MCP servers follow a consistent implementation pattern:
   - `MCPServerStdio` for process communication
   - Async tool functions for agent integration
   - Error handling and response normalization

2. Each integration includes:
   - Server class in `mcp_server.py`
   - Tool functions in `simple_agent.py`
   - Tool definitions in the agent's `TOOLS` array
   - System prompt documentation

## Testing

All integrations have been manually tested with:
- Tool registration and validation
- Basic operations of each MCP server
- Error handling for invalid inputs
- Path validation for filesystem operations

## Future Work

1. Add more comprehensive unit tests for each MCP server
2. Enhance error handling and recovery
3. Add more specialized memory structures (e.g., conversation summaries, product preferences)
4. Implement more sophisticated filesystem templates

## Dependencies

These integrations require the following NPM packages:
- `server-memory`
- `server-fetch`
- `server-sequential-thinking`
- `server-filesystem`

These are automatically installed via npx during server initialization.