#!/usr/bin/env python3
"""
Test the model parameter handling logic
"""
from app.config.agent_model_manager import AgentModelManager
from app.config.llm_factory import Provider

def test_model_params():
    manager = AgentModelManager()
    
    # Test different model types
    test_cases = [
        ("gpt-5-chat", Provider.OPENROUTER, "GPT-5 series should have no params"),
        ("gpt-5-mini", Provider.OPENAI, "GPT-5 mini should have no params"),
        ("gpt-4o", Provider.OPENAI, "GPT-4 should use max_completion_tokens"),
        ("z-ai/glm-4.5-air:free", Provider.OPENROUTER, "GLM should use max_tokens"),
        ("claude-3-5-sonnet-20241022", Provider.ANTHROPIC, "Claude should use max_tokens"),
    ]
    
    print("🧪 Testing Model Parameter Logic")
    print("=" * 50)
    
    for model_name, provider, description in test_cases:
        print(f"\n📋 Test: {description}")
        print(f"   Model: {model_name}")
        print(f"   Provider: {provider}")
        
        params = manager._get_model_parameters(model_name, 0.7, 1024, provider)
        print(f"   Result: {params}")
        
        # Validate expectations
        is_gpt5 = any(x in model_name.lower() for x in ['gpt-5', 'gpt5'])
        is_openai = provider == Provider.OPENAI or any(x in model_name.lower() for x in ['gpt-', 'o1-'])
        
        if is_gpt5:
            assert len(params) == 0, f"GPT-5 should have no params, got {params}"
            print("   ✅ Correctly excluded all params for GPT-5")
        elif is_openai and not is_gpt5:
            assert "max_completion_tokens" in params, f"OpenAI should use max_completion_tokens"
            assert "temperature" in params, f"Non-GPT-5 should have temperature"
            print("   ✅ Correctly used max_completion_tokens for OpenAI")
        else:
            assert "max_tokens" in params, f"Non-OpenAI should use max_tokens"
            assert "temperature" in params, f"Non-GPT-5 should have temperature"
            print("   ✅ Correctly used max_tokens for non-OpenAI")

if __name__ == "__main__":
    test_model_params()
    print("\n🎉 All tests passed!")