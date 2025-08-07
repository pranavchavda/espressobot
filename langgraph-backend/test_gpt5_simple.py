#!/usr/bin/env python3
"""
Simple test to verify GPT-5 is working
"""
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_gpt5():
    from app.config.llm_factory import llm_factory
    
    print("\n🚀 Testing GPT-5 Models via OpenAI API")
    print("="*50)
    
    models = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
    
    for model in models:
        try:
            print(f"\nTesting {model}...")
            llm = llm_factory.create_llm(model)
            response = await llm.ainvoke(f"Complete this: The model responding is {model} and I can")
            content = response.content if hasattr(response, 'content') else str(response)
            print(f"✅ {model}: {content[:100]}")
        except Exception as e:
            print(f"❌ {model}: {str(e)[:100]}")
    
    print("\n" + "="*50)
    print("GPT-5 models are working! 🎉")

if __name__ == "__main__":
    asyncio.run(test_gpt5())