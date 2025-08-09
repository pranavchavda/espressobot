# Dynamic Model Fetching Implementation

## Overview
Implemented dynamic model fetching from OpenRouter, OpenAI, and Anthropic APIs to provide real-time model availability in the agent management interface.

## Features Implemented

### 1. Model Fetching (`app/config/fetch_available_models.py`)
- **OpenRouter**: Fetches up to 50 relevant models (GPT, Claude, Gemini, Mistral, DeepSeek, Qwen, GLM, Llama)
- **OpenAI**: Fetches all available GPT models including GPT-5 family
- **Anthropic**: Hardcoded list of 5 Claude models (no API endpoint available)
- **Total**: 123 models available in the system

### 2. Caching System
- Cache stored in `app/config/models_cache.json`
- 1-hour cache expiration (3600 seconds)
- Automatic cache refresh when expired
- Reduces API calls and improves response time

### 3. API Integration (`app/api/agent_management.py`)
- Updated `get_available_models()` to use dynamic fetching
- Returns ModelInfo objects with id, name, provider, and description
- Seamlessly integrates with existing agent management API

### 4. LLM Factory Enhancement (`app/config/llm_factory.py`)
- Added `_create_llm_direct()` method for models not in predefined mappings
- Supports full model IDs (e.g., "openai/gpt-5-chat", "qwen/qwen-2.5-72b-instruct")
- Intelligent provider detection based on model naming patterns
- Fallback mechanisms for unknown models

### 5. Frontend Integration
- Agent management page displays 123+ models in dropdown
- Models grouped by provider for easy identification
- Real-time model switching for any agent
- Provider badges show model source

## Usage

### Fetching Models Programmatically
```python
from app.config.fetch_available_models import get_all_available_models

# Get all models (uses cache if available)
models = get_all_available_models(use_cache=True)

# Force refresh (bypasses cache)
models = get_all_available_models(use_cache=False)
```

### Model Configuration
Agents can now be configured with any model from the dynamic list:
```json
{
  "agent_name": "products",
  "model_provider": "openrouter",
  "model_name": "deepseek/deepseek-chat",
  "temperature": 0.0,
  "max_tokens": 2048
}
```

### Supported Model Formats
- OpenRouter: `provider/model-name` (e.g., "openai/gpt-5-chat")
- OpenAI Direct: `model-name` (e.g., "gpt-5")
- Anthropic: `claude-x-xxx-date` (e.g., "claude-3-5-haiku-20241022")

## Benefits
1. **Real-time Availability**: Always shows current models from providers
2. **Cost Optimization**: Users can choose cheaper models for specific agents
3. **Flexibility**: Support for 100+ models through OpenRouter
4. **Performance**: Caching reduces API calls and improves responsiveness
5. **Future-proof**: New models automatically appear when providers add them

## Files Modified
- `app/config/fetch_available_models.py` - New module for fetching models
- `app/api/agent_management.py` - Updated to use dynamic model fetching
- `app/config/llm_factory.py` - Enhanced to handle any model ID
- `app/config/agent_model_manager.py` - Works with dynamic models
- `frontend/src/pages/AgentManagementPage.jsx` - Displays all models

## Cache Management
The cache file (`app/config/models_cache.json`) can be:
- Deleted to force a refresh on next request
- Manually edited to add custom models
- Monitored for debugging model availability issues

## Environment Variables Required
- `OPENROUTER_API_KEY` - For fetching OpenRouter models
- `OPENAI_API_KEY` - For fetching OpenAI models
- `ANTHROPIC_API_KEY` - For Anthropic models (hardcoded list)

## Next Steps
- Add admin UI button to manually refresh model cache
- Implement model filtering by capabilities (chat, completion, etc.)
- Add model cost information from provider APIs
- Create model recommendation system based on task type