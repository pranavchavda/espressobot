# Agent Management System - Implementation Guide

## Overview
The Agent Management System allows dynamic configuration of LLM models for each agent in the EspressoBot system through a web UI. Changes take effect immediately without requiring system restart.

## Architecture

### Components

1. **Backend API** (`app/api/agent_management.py`)
   - REST endpoints for agent configuration
   - Dynamic agent discovery
   - Model persistence

2. **Agent Discovery** (`app/api/agent_discovery.py`)
   - Scans system for running agents
   - Returns actual agents, not hardcoded list
   - Extracts agent metadata

3. **Model Manager** (`app/config/agent_model_manager.py`)
   - Centralized model configuration
   - Dynamic model creation via LLM factory
   - Configuration persistence

4. **Configuration Storage** (`app/config/agent_models.json`)
   - JSON file for persistent configuration
   - Survives system restarts
   - Per-agent model settings

5. **Frontend UI** (`/agent-management` route)
   - Grid view of all agents
   - Model selection dropdowns
   - Real-time updates

## API Endpoints

### GET /api/agent-management/agents
Returns all discovered agents with their current configurations:
```json
{
  "success": true,
  "agents": [
    {
      "id": "orchestrator",
      "agent_name": "orchestrator",
      "agent_type": "orchestrator",
      "model_slug": "openai/gpt-5-chat",
      "model_provider": "openrouter",
      "temperature": 0.0,
      "max_tokens": 2048,
      "description": "Handles routing and general conversation",
      "source": "running",
      "configurable": true
    },
    // ... more agents
  ]
}
```

### GET /api/agent-management/models
Returns available models:
```json
{
  "success": true,
  "models": [
    {"id": "gpt-5-chat", "name": "GPT-5 Chat", "provider": "openrouter"},
    {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "provider": "anthropic"},
    // ... more models
  ],
  "provider": "openrouter"
}
```

### PUT /api/agent-management/agents/{agent_id}
Update an agent's model:
```json
{
  "model_slug": "gpt-5-mini"
}
```

### POST /api/agent-management/sync
Sync agents from the running system.

### GET /api/agent-management/stats
Get statistics about agents and models.

## Discovered Agents (14 total)

1. **orchestrator** - Routes requests and handles general conversation
2. **products** - Product searches, SKU lookups, product information
3. **pricing** - Price updates, discounts, pricing strategies
4. **inventory** - Stock levels, inventory management
5. **sales** - MAP sales, promotions, discounts
6. **features** - Product features, descriptions, metafields
7. **media** - Images and media management
8. **integrations** - System integrations and connections
9. **product_management** - Complex product creation, variants
10. **utility** - General operations and utilities
11. **graphql** - Direct GraphQL operations
12. **orders** - Sales data, revenue, order analytics
13. **google_workspace** - Google services integration
14. **ga4_analytics** - Google Analytics 4 data

## Available Models

### OpenRouter Models
- **gpt-5-chat** - Latest GPT-5 chat model
- **gpt-5** - GPT-5 reasoning model
- **gpt-5-mini** - Smaller, faster GPT-5
- **gpt-5-nano** - Smallest GPT-5 model
- **gpt-4.1** - Enhanced GPT-4
- **deepseek-chat** - Good for code/data tasks
- **qwen-2-72b** - Large multilingual model
- **glm-4.5** - Chinese-English bilingual

### Anthropic Models
- **claude-3-opus-20240229** - Most capable Claude
- **claude-3-5-haiku-20241022** - Fast and efficient
- **claude-3-haiku-20240307** - Earlier Haiku version

## Implementation Details

### Agent Model Loading
All agents now use dynamic model configuration:
```python
from app.config.agent_model_manager import agent_model_manager

class SomeAgent:
    def __init__(self):
        self.name = "agent_name"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")
```

### Configuration Persistence
Configurations are saved to `app/config/agent_models.json`:
```json
{
  "products": {
    "agent_name": "products",
    "agent_type": "specialist",
    "model_provider": "openrouter",
    "model_name": "gpt-5-mini",
    "temperature": 0.0,
    "max_tokens": 2048,
    "description": "Product searches...",
    "configurable": true
  }
}
```

### Model Factory Integration
The system uses the existing `llm_factory` to create models with proper provider configuration:
- Automatically detects available API keys
- Falls back to alternative providers if needed
- Supports OpenRouter, OpenAI, and Anthropic

## Usage

### Via Web UI
1. Navigate to `/agent-management` in the frontend
2. View all agents in the grid
3. Select a new model from the dropdown
4. Changes apply immediately

### Via API
```bash
# Get all agents
curl http://localhost:8000/api/agent-management/agents

# Update an agent's model
curl -X PUT http://localhost:8000/api/agent-management/agents/products \
  -H "Content-Type: application/json" \
  -d '{"model_slug": "gpt-5-mini"}'
```

## Testing

Run the test scripts:
```bash
# Test API endpoints
python test_agent_management.py

# Test dynamic model changes
python test_dynamic_model_change.py
```

## Notes

- Changes take effect on the next agent invocation
- No system restart required
- Configurations persist across restarts
- All 14 agents support dynamic model configuration
- The orchestrator defaults to GPT-5-chat
- Specialist agents default to Claude 3.5 Haiku

## Future Enhancements

1. **Temperature and Max Tokens**: Currently fixed, could be made configurable
2. **System Prompts**: Could allow editing agent prompts via UI
3. **Model Testing**: Add ability to test models before applying
4. **Usage Analytics**: Track which models perform best for each agent
5. **Cost Tracking**: Monitor costs per agent/model combination