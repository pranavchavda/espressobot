#!/usr/bin/env python
"""
Test script for LangSmith tracing
"""
import os
import asyncio
import logging
from langchain_openai import ChatOpenAI
from langsmith import Client

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
os.environ["LANGSMITH_PROJECT"] = "espressobot"

async def test_simple_tracing():
    """Test basic LangSmith tracing with a simple LLM call"""
    
    print("\n" + "="*50)
    print("Testing LangSmith Tracing")
    print("="*50)
    
    # Check configuration
    print("\nConfiguration:")
    print(f"  LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
    print(f"  LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
    print(f"  LANGSMITH_API_KEY: {'✓ Set' if os.getenv('LANGSMITH_API_KEY') else '✗ Not set'}")
    
    try:
        # Initialize LangSmith client
        client = Client()
        print("\n✅ LangSmith client initialized successfully")
        
        # Create a simple LLM
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Make a test call
        print("\n📤 Sending test message to LLM...")
        response = await llm.ainvoke("Say 'Hello from LangSmith tracing test!'")
        
        print(f"\n📥 Response: {response.content}")
        
        print("\n" + "="*50)
        print("✅ Test completed successfully!")
        print("\n📊 Check your traces at:")
        print(f"https://smith.langchain.com/o/336cb8ba-b6ab-42fa-85a4-9c079014f4ce/projects/p/espressobot/runs")
        print("="*50 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_tracing())