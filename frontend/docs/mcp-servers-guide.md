# MCP Servers Configuration Guide

## Overview

EspressoBot now supports easy integration of external MCP (Model Context Protocol) servers, similar to Claude Code, Claude Desktop, and Cursor. You can add any MCP server by simply editing the `mcp-servers.json` configuration file.

## Configuration File

The MCP servers are configured in `/frontend/mcp-servers.json`. The file uses a standard format compatible with other MCP clients:

```json
{
  "mcpServers": {
    "server-name": {
      "description": "Human-readable description",
      "enabled": true,
      "type": "stdio",
      "command": "command-to-run",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

## Configuration Options

### Basic Fields

- **`server-name`**: Unique identifier for the server (used internally)
- **`description`**: Human-readable description shown in logs
- **`enabled`**: Boolean to enable/disable the server (default: true)
- **`type`**: Communication type (always "stdio" for now)

### Command Execution

Two ways to specify the command:

1. **Separate command and args**:
   ```json
   "command": "npx",
   "args": ["-y", "@modelcontextprotocol/server-fetch"]
   ```

2. **Full command string**:
   ```json
   "fullCommand": "npx -y @modelcontextprotocol/server-fetch"
   ```

### Environment Variables

Optional environment variables for the server:
```json
"env": {
  "API_KEY": "your-api-key",
  "OTHER_VAR": "value"
}
```

## Examples

### 1. Fetch Server (Web Content)
```json
{
  "mcpServers": {
    "fetch": {
      "description": "MCP server for fetching web content",
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    }
  }
}
```

### 2. GitHub Server
```json
{
  "mcpServers": {
    "github": {
      "description": "GitHub API access",
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "your-github-token"
      }
    }
  }
}
```

### 3. Multiple Servers
```json
{
  "mcpServers": {
    "fetch": {
      "description": "Web content fetcher",
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    },
    "filesystem": {
      "description": "File system operations",
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "env": {
        "ALLOWED_PATHS": "/home/user/documents"
      }
    },
    "slack": {
      "description": "Slack integration",
      "enabled": false,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-slack"],
      "env": {
        "SLACK_TOKEN": "xoxb-your-token"
      }
    }
  }
}
```

## Hot Reload

The configuration file is watched for changes. When you modify `mcp-servers.json`:

1. **New servers** are automatically connected
2. **Modified servers** are reloaded with new settings
3. **Disabled servers** (enabled: false) are disconnected
4. **Removed servers** are disconnected

No need to restart EspressoBot!

## Available MCP Servers

Popular MCP servers from the community:

### Official Servers
- `@modelcontextprotocol/server-fetch` - Fetch web content
- `@modelcontextprotocol/server-github` - GitHub integration
- `@modelcontextprotocol/server-gitlab` - GitLab integration
- `@modelcontextprotocol/server-slack` - Slack integration
- `@modelcontextprotocol/server-filesystem` - File system access
- `@modelcontextprotocol/server-postgres` - PostgreSQL access
- `@modelcontextprotocol/server-sqlite` - SQLite access

### Community Servers
- `mcp-omnisearch` - Multi-source search
- `mcp-sequentialthinking-tools` - Sequential thinking tools
- `@shopify/dev-mcp` - Shopify development tools

Find more at: https://github.com/modelcontextprotocol/servers

## Built-in Servers

EspressoBot includes these built-in MCP servers that are always available:

- **`python-tools`**: EspressoBot's Python tools for Shopify operations

These cannot be disabled or modified through the configuration file.

## Troubleshooting

### Server Not Connecting
1. Check the server is installed: `npx -y @server-name`
2. Verify the command and args are correct
3. Check environment variables are set
4. Look at console logs for error messages

### Tools Not Available
1. Ensure the server is enabled in config
2. Check the server connected successfully in logs
3. Verify the server exports the expected tools

### Permission Issues
Some servers require specific permissions:
- File system servers need path access
- API servers need valid tokens
- Database servers need connection strings

### Known Limitations
- **Architecture Pattern**: The OpenAI SDK expects MCP servers to be passed to agents via the `mcpServers` array, not called directly as tools
- **Current Implementation**: Our orchestrator wraps MCP tools for direct execution, which differs from the SDK's intended pattern
- **Workaround**: MCP servers work correctly when used through dedicated agents with proper `mcpServers` configuration

### Future Improvements
To fully align with OpenAI SDK v0.11+:
1. Pass MCP servers to agents via `mcpServers` array instead of wrapping as tools
2. Let agents handle MCP tool discovery and execution automatically
3. This would provide better compatibility with all MCP server types

## Security Notes

1. **API Keys**: Store sensitive keys in environment variables, not in the config
2. **Path Access**: Be careful with filesystem servers - limit allowed paths
3. **Command Execution**: Only use trusted MCP servers
4. **Network Access**: Some servers make external API calls

## Integration with Agents

All MCP tools are automatically available to:
- The main orchestrator
- Bash agents (through tool calls)
- SWE agents
- Any custom agents you create

Tools from all servers are aggregated and presented as a unified toolkit.

## Example: Adding a Custom Server

1. Create or install your MCP server
2. Add to `mcp-servers.json`:
   ```json
   {
     "mcpServers": {
       "my-custom-tool": {
         "description": "My custom MCP server",
         "enabled": true,
         "type": "stdio",
         "command": "node",
         "args": ["/path/to/my-server/index.js"],
         "env": {
           "CONFIG_PATH": "/path/to/config.json"
         }
       }
     }
   }
   ```
3. Save the file - the server connects automatically
4. Use the tools in your prompts!

## Best Practices

1. **Naming**: Use descriptive server names (kebab-case)
2. **Descriptions**: Add clear descriptions for logging
3. **Environment**: Use env vars for sensitive data
4. **Testing**: Test servers individually before combining
5. **Monitoring**: Check logs for connection status

---

*For more information about MCP, visit: https://modelcontextprotocol.io*