# EspressoBot LangGraph Migration

## Overview

This directory contains the complete migration plan for transitioning EspressoBot from the OpenAI Agents SDK to LangGraph, a production-ready, open-source Python framework for multi-agent orchestration.

## Why LangGraph?

### Current Challenges with OpenAI Agents SDK
- Complex tool execution issues (as documented in CLAUDE.md)
- High token costs from SDK overhead
- Tight coupling to OpenAI's architecture
- Limited control over agent orchestration
- JavaScript ecosystem limitations for AI workflows

### LangGraph Advantages
- **100% Open Source** (Apache 2.0 license)
- **No vendor lock-in** - runs entirely on our infrastructure
- **Native MCP support** - direct integration with our existing Python MCP servers
- **Production features** - checkpointing, state persistence, error recovery
- **Better debugging** - Python's superior AI tooling
- **Cost efficiency** - reduced token usage, easier local model integration

## Migration Strategy

We're building a **parallel application** that will:
1. Run alongside the current system during development
2. Use SQLite for local testing
3. Maintain 100% compatibility with the existing React frontend
4. Preserve all existing functionality (dashboard, price monitor, etc.)
5. Eventually replace the Node.js backend with Python/FastAPI

## Architecture Comparison

### Current Architecture
```
React Frontend
    ↓ SSE/WebSocket
Node.js + OpenAI Agents SDK
    ├── Complex agent handoffs
    ├── MCP server spawning
    └── PostgreSQL
```

### New Architecture
```
React Frontend (unchanged)
    ↓ SSE/WebSocket
Python FastAPI + LangGraph
    ├── Graph-based orchestration
    ├── Direct MCP integration
    └── SQLite → PostgreSQL
```

## Project Structure

```
langgraph-migration/
├── README.md                 # This file
├── MIGRATION_PLAN.md        # Detailed phase-by-phase plan
├── ARCHITECTURE.md          # Technical architecture details
├── CHECKLIST.md            # Migration checklist
├── requirements.txt        # Python dependencies
└── examples/              # Code examples
    ├── agent_node_example.py
    ├── mcp_integration.py
    ├── sse_endpoint.py
    └── state_management.py
```

## Timeline

- **Week 1-2**: Build core LangGraph backend
- **Week 3**: Local testing with SQLite
- **Week 4**: Integration testing with frontend
- **Week 5**: Production migration
- **Week 6**: Monitoring and optimization

## Key Benefits

1. **Zero Frontend Changes** - React app remains untouched
2. **Reuse All MCP Servers** - 14 existing Python tools work as-is
3. **Better Performance** - ~30-40% token reduction
4. **Enhanced Reliability** - State checkpointing and recovery
5. **Cleaner Architecture** - Native Python, better separation of concerns

## Getting Started

1. Review `MIGRATION_PLAN.md` for detailed implementation steps
2. Check `ARCHITECTURE.md` for technical design decisions
3. See `examples/` for code patterns
4. Follow `CHECKLIST.md` during migration

## Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)
- [MCP Protocol Spec](https://modelcontextprotocol.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Status

Migration planning completed: January 5, 2025
Implementation start: January 6, 2025