#!/usr/bin/env python3
"""Test OpenRouter integration"""
import os
import asyncio
import logging
from app.api.title_generator import TitleGenerator
from app.config.llm_factory import LLMFactory

logging.basicConfig(level=logging.INFO)

async def test_openrouter():
    print("=" * 60)
    print("Testing OpenRouter Integration")
    print("=" * 60)
    
    # Check API keys
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    print("\n1. API Keys Status:")
    if openrouter_key and openrouter_key != "your_openrouter_api_key_here":
        print("   ✅ OPENROUTER_API_KEY is configured")
    else:
        print("   ❌ OPENROUTER_API_KEY is NOT configured")
    
    if openai_key and openai_key != "your_openai_api_key_here":
        print("   ✅ OPENAI_API_KEY is configured")
    else:
        print("   ❌ OPENAI_API_KEY is NOT configured")
    
    # Test LLM Factory
    print("\n2. Testing LLM Factory:")
    try:
        factory = LLMFactory()
        print(f"   Available providers: {[p.value for p in factory.available_providers]}")
    except Exception as e:
        print(f"   ❌ Error initializing factory: {e}")
        return False
    
    # Test Title Generator
    print("\n3. Testing Title Generator:")
    try:
        generator = TitleGenerator()
        test_message = "Can you help me find the best espresso machine for under $1000?"
        print(f"   Test message: {test_message}")
        title = await generator.generate_title(test_message)
        print(f"   Generated title: {title}")
        print("   ✅ Title generation successful")
    except Exception as e:
        print(f"   ❌ Error generating title: {e}")
        return False
    
    # Test Orchestrator Model
    print("\n4. Testing Orchestrator Model Creation:")
    try:
        llm = factory.create_llm(
            model_name="gpt-5",
            temperature=0.0,
            max_tokens=2048
        )
        print(f"   ✅ Orchestrator model created successfully")
        print(f"   Model type: {type(llm).__name__}")
    except Exception as e:
        print(f"   ❌ Error creating orchestrator model: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ All tests passed successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_openrouter())
    exit(0 if success else 1)