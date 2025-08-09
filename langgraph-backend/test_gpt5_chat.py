#!/usr/bin/env python3
"""Test GPT-5-chat model through OpenRouter"""
import os
import asyncio
import logging
from app.config.llm_factory import llm_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_gpt5_chat():
    print("=" * 60)
    print("Testing GPT-5-chat through OpenRouter")
    print("=" * 60)
    
    # Test basic invocation
    print("\n1. Testing basic invocation:")
    try:
        llm = llm_factory.create_llm(
            model_name="gpt-5-chat",
            temperature=0.0,
            max_tokens=100
        )
        
        response = await llm.ainvoke("Say 'Hello from GPT-5-chat!' and nothing else.")
        print(f"   Response: {response.content}")
        print("   ✅ Basic invocation successful")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test streaming
    print("\n2. Testing streaming:")
    try:
        chunks = []
        async for chunk in llm.astream("Count from 1 to 5"):
            if hasattr(chunk, 'content') and chunk.content:
                chunks.append(chunk.content)
                print(f"   Chunk: {repr(chunk.content)}")
        
        full_response = "".join(chunks)
        print(f"   Full response: {full_response}")
        print("   ✅ Streaming successful")
    except Exception as e:
        print(f"   ❌ Streaming error (expected if org verification needed): {e}")
        print("   Testing non-streaming fallback...")
        
        try:
            response = await llm.ainvoke("Count from 1 to 5")
            print(f"   Fallback response: {response.content}")
            print("   ✅ Non-streaming fallback successful")
        except Exception as e2:
            print(f"   ❌ Fallback also failed: {e2}")
            return False
    
    print("\n" + "=" * 60)
    print("✅ GPT-5-chat test completed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = asyncio.run(test_gpt5_chat())
    exit(0 if success else 1)