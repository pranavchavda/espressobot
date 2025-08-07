#!/usr/bin/env python3
"""
Test LLM providers and GPT-5 availability
"""
import os
import asyncio
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_providers():
    """Test all configured LLM providers"""
    from app.config.llm_factory import llm_factory
    
    print("\n" + "="*60)
    print("🧪 Testing LLM Providers")
    print("="*60 + "\n")
    
    # Check which providers are configured
    print("📋 Configured Providers:")
    print(f"   OpenRouter: {'✅' if os.getenv('OPENROUTER_API_KEY') else '❌'}")
    print(f"   OpenAI:     {'✅' if os.getenv('OPENAI_API_KEY') else '❌'}")
    print(f"   Anthropic:  {'✅' if os.getenv('ANTHROPIC_API_KEY') else '❌'}")
    print()
    
    # Test each provider
    results = llm_factory.test_providers()
    
    print("🔬 Provider Tests:")
    for provider, result in results.items():
        if result["status"] == "success":
            print(f"   {provider}: ✅ {result['response']}")
        else:
            print(f"   {provider}: ❌ {result['error']}")
    print()
    
    # Test GPT-5 models specifically
    print("🚀 Testing GPT-5 Models:")
    
    gpt5_models = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
    
    for model in gpt5_models:
        try:
            llm = llm_factory.create_llm(model)
            response = llm.invoke(f"Say 'Hello from {model}' and nothing else.")
            content = response.content if hasattr(response, 'content') else str(response)
            print(f"   {model}: ✅ {content[:50]}")
        except Exception as e:
            print(f"   {model}: ❌ {str(e)[:100]}")
    
    print("\n" + "="*60 + "\n")

async def test_a2a_with_gpt5():
    """Test A2A orchestration with GPT-5"""
    print("🤖 Testing A2A Orchestration with GPT-5")
    print("-"*60 + "\n")
    
    # Set environment to use GPT-5 for orchestration
    os.environ["MODEL_ORCHESTRATOR"] = "openai/gpt-5"
    os.environ["MODEL_PRIMARY"] = "openai/gpt-5-mini"
    os.environ["MODEL_AUXILIARY"] = "openai/gpt-5-nano"
    
    from app.orchestrator_a2a import A2AOrchestrator
    
    try:
        orchestrator = A2AOrchestrator()
        
        # Test with a complex query
        test_query = "Show me the Breville Barista Express with current pricing and stock levels"
        
        print(f"Query: {test_query}")
        print("Processing...\n")
        
        result = await orchestrator.run(
            message=test_query,
            thread_id="test-gpt5-a2a"
        )
        
        print("Results:")
        print(f"Response: {result.get('response', 'No response')[:200]}...")
        print(f"Execution Path: {' → '.join(result.get('execution_path', []))}")
        print(f"Agents Involved: {', '.join(result.get('agents_involved', []))}")
        print(f"A2A Requests: {len(result.get('a2a_requests', []))} inter-agent communications")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "="*60 + "\n")

async def main():
    """Run all tests"""
    await test_providers()
    
    # Only test A2A if we have at least one provider configured
    if any([
        os.getenv('OPENROUTER_API_KEY'),
        os.getenv('OPENAI_API_KEY'),
        os.getenv('ANTHROPIC_API_KEY')
    ]):
        await test_a2a_with_gpt5()
    else:
        print("⚠️  No API keys configured. Please set OPENROUTER_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY")

if __name__ == "__main__":
    asyncio.run(main())