# Model Context Protocol (MCP) Implementation

This document explains the Model Context Protocol (MCP) implementation for the Flask Shopify Bot.

## Overview

The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context to LLMs (Large Language Models). It's similar to a USB-C port for AI applications - providing a universal way to connect LLMs to data sources and external tools.

MCP allows you to build servers that expose data and functionality to LLM applications in a secure, standardized way. MCP servers can expose data through Resources (similar to GET requests), provide functionality through Tools (similar to POST/PUT requests), and define interaction patterns through Prompts (reusable templates).

This project contains an implementation of several MCP servers, some using official packages where available and others using simplified implementations.

## Included Implementations

1. **Memory Server** (`memory_mcp_server`): Provides persistent memory capabilities across conversations
   - Uses our simplified implementation as this requires npm package `@modelcontextprotocol/server-memory`

2. **Fetch Server** (`fetch_mcp_server`): Handles web content retrieval
   - Can use the Python package `mcp-server-fetch` which we've installed

3. **Sequential Thinking Server** (`thinking_mcp_server`): Formalizes the thinking process
   - Uses our simplified implementation as this requires npm package `@modelcontextprotocol/server-sequential-thinking`

4. **Filesystem Server** (`filesystem_mcp_server`): Manages file operations in a controlled environment
   - Uses our simplified implementation as this requires npm package `@modelcontextprotocol/server-filesystem`

## Memory System

The memory system combines a simple in-memory store with database persistence to provide user-specific memory storage:

- `simple_memory.py`: Implements a simple in-memory storage with user isolation
- `memory_service.py`: Combines in-memory storage with database persistence

### Memory Usage Example

```python
# Storing a memory
result = await memory_service.store_memory(
    user_id=1,
    key="preferences",
    value={"theme": "dark", "language": "en"}
)

# Retrieving a memory
result = await memory_service.retrieve_memory(
    user_id=1,
    key="preferences"
)

# Listing all memories for a user
result = await memory_service.list_memories(user_id=1)

# Deleting a memory
result = await memory_service.delete_memory(
    user_id=1,
    key="preferences"
)
```

## Fetch System

The fetch system provides tools for retrieving and processing web content:

- `fetch_url`: Fetches raw content from a URL with metadata
- `fetch_and_extract_text`: Fetches a webpage and extracts text content, with optional CSS selector filtering
- `fetch_json`: Fetches and parses JSON from a URL

### Fetch Usage Example

```python
# Fetching raw content
result = await fetch_mcp_server.fetch_url(
    url="https://example.com",
    options={"headers": {"User-Agent": "MyBot/1.0"}}
)

# Extracting text content
result = await fetch_mcp_server.fetch_and_extract_text(
    url="https://example.com",
    selector="article.main-content"
)

# Fetching JSON
result = await fetch_mcp_server.fetch_json(
    url="https://api.example.com/data.json"
)
```

## Sequential Thinking System

The sequential thinking system formalizes the thinking process into structured steps:

- `think`: General step-by-step thinking on any prompt
- `solve_problem`: Problem-solving thinking with a focus on understanding, breaking down, and evaluating solutions
- `plan_code`: Code planning with a focus on requirements, implementation details, and testing approach

### Sequential Thinking Usage Example

```python
# General thinking
result = await thinking_mcp_server.think(
    prompt="What would be the best approach to improve customer engagement?",
    thinking_type="general",
    max_steps=5
)

# Problem solving
result = await thinking_mcp_server.solve_problem(
    problem="How to reduce cart abandonment rates?",
    max_steps=6
)

# Code planning
result = await thinking_mcp_server.plan_code(
    coding_task="Implement a recommendation engine based on browsing history",
    max_steps=7
)
```

## Filesystem System

The filesystem system provides controlled access to read and write files in specific directories:

- `read_file`: Read a file from the controlled storage
- `write_file`: Write content to a file in the controlled storage
- `list_directory`: List contents of a directory
- `delete_file`: Delete a file
- `check_file_exists`: Check if a file exists

### Filesystem Usage Example

```python
# Reading a file
result = await filesystem_mcp_server.read_file(
    path="templates/email_template.html",
    user_id=1
)

# Writing a file
result = await filesystem_mcp_server.write_file(
    path="exports/report.csv",
    content="id,name,value\n1,Test,100",
    user_id=1
)

# Listing a directory
result = await filesystem_mcp_server.list_directory(
    path="templates",
    user_id=1
)
```

## Storage Organization

The filesystem server organizes files into specific directories:

- `storage/templates/`: For reusable templates
- `storage/exports/`: For generated exports (CSV, JSON, etc.)
- `storage/users/{user_id}/`: User-specific files

## Integration with Agent System

These implementations are integrated into the simple_agent.py file as tools that the AI agent can use. The TOOLS array defines the available tools, and the tool_functions dictionary maps tool names to their implementations.

## Testing

Each implementation includes a test script to verify functionality:

- `test_simple_memory.py`: Tests the memory server implementation
- `test_memory_system.py`: Tests the combined memory service with database integration

## Switching to Actual MCP Servers

To switch to the actual MCP servers in the future:

### For Python-based servers (Fetch)

1. Install the required Python package (already done):
   ```
   pip install mcp-server-fetch
   ```

2. Update `mcp_server.py` to use the actual MCP server configuration:
   ```python
   # Example for fetch server
   fetch_server_config = {
     "command": "uvx",  # Or appropriate Python command
     "args": ["mcp-server-fetch"]
   }
   ```

### For npm-based servers (Memory, Sequential Thinking, Filesystem)

1. Install the required npm packages:
   ```
   npm install -g @modelcontextprotocol/server-memory
   npm install -g @modelcontextprotocol/server-sequential-thinking
   npm install -g @modelcontextprotocol/server-filesystem
   ```

2. Update `mcp_server.py` to use the actual MCP server classes with correct configurations:
   ```python
   # Example configuration
   memory_server_config = {
     "command": "npx",
     "args": ["-y", "@modelcontextprotocol/server-memory"]
   }
   ```

3. Update the imports in `memory_service.py` as needed