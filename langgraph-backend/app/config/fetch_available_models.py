"""
Fetch available models from OpenRouter, OpenAI, Anthropic, and Perplexity APIs
"""
import os
import logging
import requests
from typing import List, Dict, Any
import json

logger = logging.getLogger(__name__)

def fetch_openrouter_models() -> List[Dict[str, Any]]:
    """Fetch available models from OpenRouter"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("No OpenRouter API key found")
        return []
    
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://idrinkcoffee.com",
                "X-Title": "EspressoBot"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            models = []
            
            # Filter for relevant models
            for model in data.get("data", []):
                model_id = model.get("id", "")
                # Focus on popular/relevant models
                if any(x in model_id.lower() for x in ["gpt", "claude", "gemini", "mistral", "deepseek", "qwen", "glm", "llama"]):
                    models.append({
                        "id": model_id,
                        "name": model.get("name", model_id),
                        "provider": "openrouter",
                        "context_length": model.get("context_length", 0),
                        "pricing": model.get("pricing", {}),
                        "description": f"via OpenRouter - {model.get('description', '')[:100]}"
                    })
            
            logger.info(f"Fetched {len(models)} models from OpenRouter")
            return models[:50]  # Limit to top 50 to avoid overwhelming the UI
        else:
            logger.error(f"OpenRouter API error: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching OpenRouter models: {e}")
        return []

def fetch_perplexity_models() -> List[Dict[str, Any]]:
    """Return a hardcoded list of Perplexity models (API endpoint deprecated)."""
    if not os.getenv("PERPLEXITY_API_KEY"):
        logger.warning("No Perplexity API key found; hiding Perplexity models from list")
        return []
    logger.info("Using hardcoded Perplexity models list (endpoint deprecated)")
    return [
        {
            "id": "perplexity/sonar-pro",
            "name": "Sonar Pro",
            "provider": "perplexity",
            "description": "Advanced model for search, reasoning, and long-form content with up-to-date citations. Supports 200k context and is optimized for complex questions and exhaustive research."
        },
        {
            "id": "perplexity/sonar",
            "name": "Sonar",
            "provider": "perplexity",
            "description": "Lightweight, fast, and cost-effective model best for quick answers and straightforward queries. Real-time web search and citations are supported."
        },
        {
            "id": "perplexity/sonar-reasoning-pro",
            "name": "Sonar Reasoning Pro",
            "provider": "perplexity",
            "description": "Premier reasoning model using chain-of-thought (CoT). Designed for complex analyses and multi-step problem solving."
        },
        {
            "id": "perplexity/sonar-reasoning",
            "name": "Sonar Reasoning",
            "provider": "perplexity",
            "description": "Fast real-time model for general reasoning and live web search tasks."
        },
        {
            "id": "perplexity/sonar-deep-research",
            "name": "Sonar Deep Research",
            "provider": "perplexity",
            "description": "Specialized for very deep, comprehensive research queries that require thorough analysis and multi-source synthesis."
        },
    ]

def fetch_openai_models() -> List[Dict[str, Any]]:
    """Fetch available models from OpenAI"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("No OpenAI API key found")
        return []
    
    try:
        response = requests.get(
            "https://api.openai.com/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            models = []
            
            for model in data.get("data", []):
                model_id = model.get("id", "")
                # Filter for chat models
                if any(x in model_id for x in ["gpt", "davinci", "turbo", "o1", "o3"]):
                    models.append({
                        "id": model_id,
                        "name": model_id,
                        "provider": "openai",
                        "description": f"OpenAI Direct - {model.get('owned_by', 'OpenAI')}"
                    })
            
            logger.info(f"Fetched {len(models)} models from OpenAI")
            return models
        else:
            logger.error(f"OpenAI API error: {response.status_code}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching OpenAI models: {e}")
        return []

def fetch_anthropic_models() -> List[Dict[str, Any]]:
    """Fetch available Anthropic models from their API"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("No Anthropic API key found")
        return []
    
    try:
        response = requests.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            models = []
            
            for model in data.get("data", []):
                model_id = model.get("id", "")
                # Only include Claude models (filter out any other types)
                if "claude" in model_id.lower():
                    models.append({
                        "id": model_id,
                        "name": model.get("display_name", model_id),
                        "provider": "anthropic",
                        "description": f"Anthropic Direct - {model.get('description', '')[:100]}" if model.get('description') else "Anthropic Direct"
                    })
            
            logger.info(f"Fetched {len(models)} models from Anthropic")
            return models
        else:
            logger.error(f"Anthropic API error: {response.status_code} - {response.text}")
            # Fallback to hardcoded list if API fails
            return get_anthropic_fallback_models()
            
    except Exception as e:
        logger.error(f"Error fetching Anthropic models: {e}")
        # Fallback to hardcoded list if API fails
        return get_anthropic_fallback_models()

def get_anthropic_fallback_models() -> List[Dict[str, Any]]:
    """Fallback hardcoded Anthropic models if API is unavailable"""
    logger.info("Using fallback Anthropic models list")
    return [
        {
            "id": "claude-3-opus-20240229",
            "name": "Claude 3 Opus",
            "provider": "anthropic",
            "description": "Most capable model for complex tasks"
        },
        {
            "id": "claude-3-sonnet-20240229",
            "name": "Claude 3 Sonnet",
            "provider": "anthropic",
            "description": "Balanced performance and speed"
        },
        {
            "id": "claude-3-haiku-20240307",
            "name": "Claude 3 Haiku",
            "provider": "anthropic",
            "description": "Fastest and most cost-effective"
        },
        {
            "id": "claude-3-5-haiku-20241022",
            "name": "Claude 3.5 Haiku",
            "provider": "anthropic",
            "description": "Latest Haiku with improved capabilities"
        },
        {
            "id": "claude-3-5-sonnet-20241022",
            "name": "Claude 3.5 Sonnet",
            "provider": "anthropic",
            "description": "Latest Sonnet with enhanced reasoning"
        }
    ]

def get_all_available_models(use_cache: bool = True) -> List[Dict[str, Any]]:
    """Get all available models from all providers"""
    cache_file = "app/config/models_cache.json"
    
    # Try to use cache if requested and it exists
    if use_cache and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
                # Check if cache is recent (less than 1 hour old)
                import time
                if time.time() - cache_data.get("timestamp", 0) < 3600:
                    models = cache_data.get("models", [])
                    # If Perplexity key is present but cache has no Perplexity models, bypass cache
                    if os.getenv("PERPLEXITY_API_KEY"):
                        has_pplx = any((m.get("provider") == "perplexity") or (str(m.get("id", "")).startswith("perplexity/")) for m in models)
                        if not has_pplx:
                            logger.info("Cache missing Perplexity models while PERPLEXITY_API_KEY is set; bypassing cache")
                        else:
                            logger.info("Using cached models list")
                            return models
                    else:
                        logger.info("Using cached models list")
                        return models
        except Exception as e:
            logger.warning(f"Could not read cache: {e}")
    
    # Fetch from all providers
    all_models = []
    
    # Fetch from each provider
    all_models.extend(fetch_openrouter_models())
    all_models.extend(fetch_openai_models())
    all_models.extend(fetch_anthropic_models())
    all_models.extend(fetch_perplexity_models())
    
    # Save to cache
    try:
        import time
        cache_data = {
            "timestamp": time.time(),
            "models": all_models
        }
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        logger.info(f"Cached {len(all_models)} models")
    except Exception as e:
        logger.warning(f"Could not save cache: {e}")
    
    return all_models

if __name__ == "__main__":
    # Test fetching models
    logging.basicConfig(level=logging.INFO)
    models = get_all_available_models(use_cache=False)
    
    print(f"\nTotal models available: {len(models)}")
    
    # Group by provider
    by_provider = {}
    for model in models:
        provider = model["provider"]
        if provider not in by_provider:
            by_provider[provider] = []
        by_provider[provider].append(model)
    
    for provider, provider_models in by_provider.items():
        print(f"\n{provider.upper()}: {len(provider_models)} models")
        for model in provider_models[:5]:  # Show first 5
            print(f"  - {model['id']}: {model['name']}")
        if len(provider_models) > 5:
            print(f"  ... and {len(provider_models) - 5} more")