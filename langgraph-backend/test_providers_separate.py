#!/usr/bin/env python3
"""
Test OpenRouter vs OpenAI separately to see which works
"""
import os
import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)

async def test_openrouter():
    """Test GPT-5 via OpenRouter"""
    print("\n🔹 Testing via OpenRouter...")
    try:
        llm = ChatOpenAI(
            model="openai/gpt-5-mini",
            max_tokens=50,
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://espressobot.com",
                "X-Title": "EspressoBot"
            }
        )
        response = await asyncio.wait_for(
            llm.ainvoke("Say 'Hello from OpenRouter GPT-5-mini'"),
            timeout=5.0
        )
        print(f"✅ OpenRouter: {response.content}")
        return True
    except asyncio.TimeoutError:
        print("❌ OpenRouter: Timeout (5s)")
        return False
    except Exception as e:
        print(f"❌ OpenRouter: {str(e)[:100]}")
        return False

async def test_openai_direct():
    """Test GPT-5 via OpenAI direct"""
    print("\n🔹 Testing via OpenAI Direct...")
    try:
        llm = ChatOpenAI(
            model="gpt-5-mini",
            max_tokens=50,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        response = await asyncio.wait_for(
            llm.ainvoke("Say 'Hello from OpenAI GPT-5-mini'"),
            timeout=5.0
        )
        print(f"✅ OpenAI: {response.content}")
        return True
    except asyncio.TimeoutError:
        print("❌ OpenAI: Timeout (5s)")
        return False
    except Exception as e:
        print(f"❌ OpenAI: {str(e)[:100]}")
        return False

async def test_gpt4_fallback():
    """Test GPT-4 as fallback"""
    print("\n🔹 Testing GPT-4 fallback via OpenAI...")
    try:
        llm = ChatOpenAI(
            model="gpt-4-turbo-preview",
            temperature=0,
            max_tokens=50,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        response = await asyncio.wait_for(
            llm.ainvoke("Say 'Hello from GPT-4'"),
            timeout=5.0
        )
        print(f"✅ GPT-4: {response.content}")
        return True
    except asyncio.TimeoutError:
        print("❌ GPT-4: Timeout (5s)")
        return False
    except Exception as e:
        print(f"❌ GPT-4: {str(e)[:100]}")
        return False

async def main():
    print("="*60)
    print("🧪 Testing Providers Separately")
    print("="*60)
    
    results = []
    
    # Test each provider
    results.append(("OpenRouter GPT-5", await test_openrouter()))
    results.append(("OpenAI GPT-5", await test_openai_direct()))
    results.append(("OpenAI GPT-4", await test_gpt4_fallback()))
    
    print("\n" + "="*60)
    print("📊 Summary:")
    for name, success in results:
        status = "✅ Working" if success else "❌ Not Working"
        print(f"   {name}: {status}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())