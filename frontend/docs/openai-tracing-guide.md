# OpenAI Tracing Guide

## Overview

OpenAI tracing provides detailed debugging information for agent execution, including tool calls, model responses, and execution flow. However, tracing can be expensive due to the token usage in trace logs.

## Configuration

Tracing is controlled via environment variables:

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `OPENAI_TRACING_ENABLED` | Enable/disable tracing globally | `false` | `true` |
| `OPENAI_TRACING_AGENTS` | Comma-separated list of agents to trace | All agents | `Products Agent,Pricing Agent` |
| `OPENAI_TRACING_MAX_OUTPUT` | Max trace output size in KB | `500` | `1000` |
| `OPENAI_TRACING_LOG_CONFIG` | Log config on startup | `true` | `false` |

### Examples

1. **Enable tracing for all agents:**
   ```bash
   OPENAI_TRACING_ENABLED=true npm run dev
   ```

2. **Enable tracing for specific agents only:**
   ```bash
   OPENAI_TRACING_ENABLED=true OPENAI_TRACING_AGENTS="Products Agent,Pricing Agent" npm run dev
   ```

3. **Enable with larger output limit:**
   ```bash
   OPENAI_TRACING_ENABLED=true OPENAI_TRACING_MAX_OUTPUT=1000 npm run dev
   ```

## Cost Considerations

⚠️ **WARNING**: Tracing can be expensive!

### Why Tracing Costs Money

1. **Tool Schemas**: MCP tools include full JSON schemas that can be 10-20KB each
2. **State Objects**: Agent state can include large context objects
3. **Multiple Calls**: Each tool call generates trace data
4. **Token Usage**: Traces count against your OpenAI API token usage

### Historical Issue

Previously, EspressoBot experienced $15+ charges from a single conversation due to:
- spawn_mcp_agent returning 5.7MB state objects
- 28 tools loaded simultaneously (300KB+ of schemas)
- Traces exceeding OpenAI's 1MB limit

### Current Safeguards

1. **Output Truncation**: Traces are automatically truncated to configured limit
2. **Specialized Agents**: Each agent loads only 1-6 tools (vs 28 previously)
3. **Selective Tracing**: Trace only specific agents when debugging
4. **No State Bloat**: Direct agent calls don't return full state objects

## Best Practices

### Development

1. **Start with specific agents**: Don't enable for all agents at once
   ```bash
   OPENAI_TRACING_ENABLED=true OPENAI_TRACING_AGENTS="Products Agent" npm run dev
   ```

2. **Use small output limits**: Start with 100-200KB
   ```bash
   OPENAI_TRACING_ENABLED=true OPENAI_TRACING_MAX_OUTPUT=100 npm run dev
   ```

3. **Monitor costs**: Check your OpenAI dashboard regularly when tracing is enabled

### Production

⚠️ **NEVER enable tracing in production unless absolutely necessary!**

If you must trace in production:
1. Use very specific agent lists
2. Set strict output limits
3. Enable for short periods only
4. Monitor costs closely

## Debugging Tips

### When to Use Tracing

- Agent is failing silently
- Tool calls aren't working as expected  
- Need to see exact prompts and responses
- Debugging complex multi-agent workflows

### Alternative Debugging Methods

Before enabling tracing, try:
1. **Console logs**: Already extensive throughout the codebase
2. **Tool result cache**: Check cached results with `search_tool_cache`
3. **Agent-specific logs**: Each agent logs its operations
4. **SSE events**: Real-time execution feedback in the UI

## Viewing Traces

When tracing is enabled, traces are:
1. Sent to OpenAI's servers
2. Viewable in the OpenAI dashboard
3. Associated with your API key
4. Retained according to OpenAI's data retention policy

To view traces:
1. Log into your OpenAI account
2. Navigate to the Usage section
3. Look for trace data associated with your API calls

## Troubleshooting

### Traces Not Appearing

1. Verify environment variable is set:
   ```bash
   echo $OPENAI_TRACING_ENABLED
   ```

2. Check startup logs for configuration:
   ```
   [Tracing Config] OpenAI tracing settings:
     - Enabled: true
     - Agents to trace: all
     - Max output size: 500KB
     - Current state: ENABLED
   ```

3. Ensure agent name matches exactly (case-sensitive)

### Traces Too Large

If you see truncation warnings:
1. Reduce `OPENAI_TRACING_MAX_OUTPUT`
2. Trace fewer agents
3. Simplify the operations being traced

### High Costs

If tracing causes high costs:
1. **Immediately disable tracing**
2. Check which agents are generating large traces
3. Use specialized agents (they load fewer tools)
4. Reduce output limits