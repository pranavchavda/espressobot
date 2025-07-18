
# EspressoBot Codebase Diagram

This document provides a high-level overview of the EspressoBot codebase structure.

```
/home/pranav/espressobot/frontend/
├───.env.example                  # Example environment variables
├───.gitignore                    # Git ignore rules
├───docs/                         # Project documentation
├───index.html                    # Main HTML entry point
├───package.json                  # Project dependencies and scripts
├───pnpm-lock.yaml                # Lockfile for pnpm
├───prisma/                       # Prisma schema and migrations
│   ├───migrations/
│   └───schema.prisma
├───public/                       # Public assets
├───python-tools/                 # Python tools for Shopify operations (used by MCP servers)
│   ├───mcp_tools/                # Modularized Python tools
│   ├───mcp-*.py                  # Specialized MCP servers
│   └───memory_operations.py      # Memory access for bash agents
├───scripts/                      # Node.js scripts for documentation management
├───server/                       # Backend server code (Node.js/Express)
│   ├───agents/                   # Agent definitions (specialized agents)
│   ├───api/                      # API route handlers
│   ├───config/                   # Configuration files (auth, tracing)
│   ├───context/                  # Context builders and managers
│   ├───memory/                   # Local memory system (SQLite, embeddings)
│   ├───native-tools/             # Native JavaScript tool implementations
│   ├───prompts/                  # System prompts for agents
│   ├───services/                 # Services like log streaming
│   ├───shopify/                  # Shopify client
│   ├───tool-docs/                # Markdown documentation for tools
│   ├───tools/                    # Core tool definitions and wrappers
│   └───espressobot1.js           # Main orchestrator logic
├───src/                          # Frontend source code (React)
│   ├───components/               # Reusable UI components
│   ├───features/                 # Feature-specific components (chat, auth)
│   ├───pages/                    # Page components
│   ├───App.jsx                   # Root React component
│   └───main.jsx                  # Main React entry point
├───tests/                        # Test files for various components
└───vite.config.js                # Vite configuration
```

---

# Unused or Deprecated Files

Based on the file list and project documentation, the following files are likely unused, deprecated, or were for one-off testing purposes:

### Backup Files
-   `_cleanup_backup/`: This directory contains backups of old agent files that have been replaced by the new agentic architecture.
-   `server/custom-tools-definitions-extended.js.bak`: A backup file, indicating it's no longer in use.
-   `python-tools/mcp_tools/products/get.py.backup`: A backup of a Python tool.
-   `python-tools/mcp_tools/sales/manage_map_sales.py.bak`: A backup of a sales management tool.

### Old Agent Implementations
-   The files within `_cleanup_backup/20250624_163710/` such as `basic-agent.js`, `super-simple-agent.js`, `dispatcher-agent.js`, etc., represent the old multi-agent system that has been deprecated in favor of the new orchestrator (`espressobot1.js`) and specialized agents.

### Redundant or Old Test Files
-   Many files in the `tests/` directory appear to be for specific, one-off diagnostics and may not be part of a regular testing suite (e.g., `test-sse-flow.js`, `test-vision-debug-sdk.js`, `test-handoff-debug.js`).
-   `test-orchestrator-api.cjs`: The `.cjs` extension suggests it might be for an older CommonJS version of the test.

### Deprecated Tools (Mentioned in Docs)
-   The documentation mentions that `manage_features_json.py` is deprecated and replaced by `manage_features_metaobjects.py`.
-   The documentation also indicates a move away from Python subprocess tools towards native MCP tools or direct agent access, making many of the individual scripts in `python-tools/` potentially obsolete in favor of the MCP servers.

### Temporary/Debug Files
-   Files in the `tmp/` directory are temporary and not part of the main codebase.
-   `test-browser-debug.html` and `test-full-ui-flow.html` seem to be for manual browser-based debugging.
