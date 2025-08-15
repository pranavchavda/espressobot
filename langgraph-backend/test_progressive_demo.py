#!/usr/bin/env python3
"""Demo of Progressive Orchestrator with GPT-5 Thinking Model"""
import requests
import json
import time
from typing import List, Tuple

def test_conversation(messages: List[str], thread_id: str) -> List[Tuple[float, str]]:
    """Run a conversation and return timing results"""
    url = "http://localhost:8000/api/agent/message"
    results = []
    
    for i, msg in enumerate(messages, 1):
        print(f"\n{'='*60}")
        print(f"Turn {i}: {msg}")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        try:
            response = requests.post(url, json={
                "message": msg,
                "thread_id": thread_id
            }, timeout=120)
            
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', 'No response')
                results.append((elapsed, response_text))
                
                print(f"⏱️  {elapsed:.1f} seconds")
                print(f"📬 {response_text[:300]}...")
                
                # Analysis
                if i == 1:
                    print("📝 Note: First query typically takes 30-50s (agent call)")
                elif elapsed < 20:
                    print("⚡ Fast! Used compressed context from previous turns")
                elif elapsed < 35:
                    print("💭 Moderate speed - GPT-5 thinking with context")
                else:
                    print("🔍 Slower - likely called agent for new information")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((0, f"Error: {e}"))
            
        time.sleep(1)
    
    return results

def main():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║     Progressive Orchestrator with GPT-5 Thinking Model       ║
╠═══════════════════════════════════════════════════════════════╣
║ Architecture: User → Orchestrator → Agent → Orchestrator → User║
║ Compression: gpt-4.1-mini via LangExtract                     ║
║ Orchestration: GPT-5 (thinking model - needs time)           ║
╚═══════════════════════════════════════════════════════════════╝
""")
    
    # Test 1: Product search with follow-ups
    print("\n🧪 TEST 1: Product Search with Context Reuse")
    print("-" * 60)
    
    thread_id = f"demo_{int(time.time())}"
    messages = [
        "Find the Gaggia Classic Pro espresso machine",
        "What's the price?",
        "Is it available in different colors?",
        "What about stock levels?"
    ]
    
    results = test_conversation(messages, thread_id)
    
    # Summary
    print(f"\n📊 SUMMARY for Thread {thread_id}:")
    print("-" * 60)
    total_time = sum(r[0] for r in results)
    print(f"Total conversation time: {total_time:.1f} seconds")
    print(f"Average response time: {total_time/len(results):.1f} seconds")
    print("\nTiming breakdown:")
    for i, (elapsed, _) in enumerate(results, 1):
        indicator = "🔍" if i == 1 else "⚡" if elapsed < 20 else "💭"
        print(f"  Turn {i}: {elapsed:.1f}s {indicator}")
    
    print(f"\n💡 Key Insights:")
    print("• First query (with agent call): ~30-50 seconds")
    print("• Follow-ups using context: ~8-20 seconds")
    print("• GPT-5 thinking time is worth it for intelligence")
    print("• Compression reduces tokens and improves speed")
    
    print(f"\n🔍 Verify compression worked:")
    print(f"grep '{thread_id}' server.log | grep 'Compressed context'")
    
    print(f"\n📈 View full trace in LangSmith:")
    print(f"https://smith.langchain.com (search: {thread_id})")

if __name__ == "__main__":
    main()