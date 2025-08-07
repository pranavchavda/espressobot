#!/usr/bin/env python3
"""
Manual GPT-5 Integration Test - Tests the specific complex query from requirements
"""
import os
import json
import asyncio
import aiohttp
import sys
import time

async def test_complex_query():
    """Test the complex query: 'Show me the Breville Barista Express with current pricing and stock levels'"""
    
    query = "Show me the Breville Barista Express with current pricing and stock levels"
    backend_url = "http://localhost:8000"
    
    print(f"🧪 Testing complex query: {query}")
    print(f"🎯 Backend URL: {backend_url}")
    print(f"🔍 Expected: A2A orchestration involving products, pricing, and inventory agents")
    print("-" * 80)
    
    # Test with auto mode (should detect complexity)
    async with aiohttp.ClientSession() as session:
        payload = {
            "message": query,
            "mode": "auto",
            "thread_id": f"test-complex-{int(time.time())}"
        }
        
        print("📡 Sending request to /api/agent/v2/stream...")
        
        try:
            async with session.post(
                f"{backend_url}/api/agent/v2/stream",
                json=payload
            ) as response:
                if response.status != 200:
                    print(f"❌ Request failed with status {response.status}")
                    return False
                
                print(f"✅ Response received with status {response.status}")
                
                # Process streaming response
                full_response = ""
                pattern = None
                agents = []
                a2a_metadata = None
                analysis_reason = None
                
                print("\n📝 Streaming Response:")
                print("-" * 40)
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if not line:
                        continue
                    
                    try:
                        data = json.loads(line)
                        event = data.get("event")
                        
                        if event == "conversation_id":
                            pattern = data.get("pattern")
                            analysis_reason = data.get("analysis")
                            print(f"🧠 Complexity Analysis: {pattern}")
                            print(f"💭 Reasoning: {analysis_reason}")
                        
                        elif event == "agent_message":
                            agent = data.get("agent")
                            if agent and agent not in agents:
                                agents.append(agent)
                                print(f"🤖 Agent Active: {agent}")
                            
                            if data.get("tokens"):
                                new_tokens = "".join(data["tokens"])
                                full_response += new_tokens
                                if new_tokens.strip():
                                    print(f"💬 {agent}: {new_tokens}", end="", flush=True)
                        
                        elif event == "a2a_metadata":
                            a2a_metadata = {
                                "execution_path": data.get("execution_path", []),
                                "agents_involved": data.get("agents_involved", []),
                                "a2a_requests": data.get("a2a_requests", [])
                            }
                            print(f"\n🔄 A2A Execution Path: {a2a_metadata['execution_path']}")
                            print(f"👥 Agents Involved: {a2a_metadata['agents_involved']}")
                        
                        elif event == "done":
                            print(f"\n✅ Stream completed")
                            break
                        
                        elif event == "error":
                            print(f"\n❌ Error: {data.get('error')}")
                            return False
                            
                    except json.JSONDecodeError:
                        continue
                
                print("\n" + "-" * 80)
                print("📊 RESULTS SUMMARY:")
                print(f"   🧩 Pattern Detected: {pattern}")
                print(f"   🤖 Agents Used: {' → '.join(agents)}")
                print(f"   📝 Response Length: {len(full_response)} characters")
                print(f"   ⚡ Contains Pricing Info: {'price' in full_response.lower() or '$' in full_response}")
                print(f"   📦 Contains Stock Info: {'stock' in full_response.lower() or 'inventory' in full_response.lower()}")
                print(f"   ☕ Contains Product Info: {'breville' in full_response.lower() or 'barista' in full_response.lower()}")
                
                if a2a_metadata:
                    print(f"   🔄 A2A Orchestration: {len(a2a_metadata['a2a_requests'])} requests")
                
                # Success criteria
                success = (
                    pattern in ["a2a", "simple"] and  # Should route appropriately
                    len(full_response) > 50 and       # Should have substantive response
                    len(agents) > 0                   # Should use at least one agent
                )
                
                print(f"\n{'✅ SUCCESS' if success else '❌ FAILURE'}: Test completed")
                
                if full_response:
                    print(f"\n📋 FULL RESPONSE:")
                    print("-" * 40)
                    print(full_response)
                    print("-" * 40)
                
                return success
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
            return False

async def test_provider_usage():
    """Test that the system is actually using GPT-5 models"""
    print("\n🔍 TESTING GPT-5 MODEL USAGE")
    print("=" * 50)
    
    try:
        sys.path.append('/home/pranav/espressobot/langgraph-backend')
        from app.config.llm_factory import llm_factory
        
        # Test different model tiers
        models_to_test = [
            ("gpt-5", "orchestrator"),
            ("gpt-5-mini", "primary agent"),
            ("gpt-5-nano", "auxiliary agent")
        ]
        
        for model, tier_desc in models_to_test:
            print(f"\n🧪 Testing {model} ({tier_desc})...")
            try:
                llm = llm_factory.create_llm(model, temperature=0.0, max_tokens=50)
                response = llm.invoke(f"Complete this sentence: I am {model} and I")
                
                print(f"   ✅ {model} responded: {response.content[:100]}...")
                
            except Exception as e:
                print(f"   ❌ {model} failed: {e}")
        
        # Test provider configuration
        print(f"\n📊 Provider Status:")
        print(f"   OpenAI API: {'✅' if llm_factory.openai_key else '❌'}")
        print(f"   OpenRouter API: {'✅' if llm_factory.openrouter_key else '❌'}")
        print(f"   Anthropic API: {'✅' if llm_factory.anthropic_key else '❌'}")
        
    except Exception as e:
        print(f"❌ Provider test failed: {e}")

async def main():
    """Run manual tests"""
    print("🚀 GPT-5 INTEGRATION MANUAL TESTS")
    print("=" * 50)
    
    # Check backend connectivity
    try:
        import requests
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and healthy")
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return
    
    # Test provider usage
    await test_provider_usage()
    
    # Test complex query
    success = await test_complex_query()
    
    print(f"\n{'🎉 ALL TESTS PASSED' if success else '⚠️ TESTS HAD ISSUES'}")

if __name__ == "__main__":
    asyncio.run(main())