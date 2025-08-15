#!/usr/bin/env python3
"""Test progressive orchestrator context preservation with GPT-5"""
import requests
import json
import time

url = "http://localhost:8000/api/agent/message"
thread_id = f"context_test_{int(time.time())}"

print(f"Testing Context Preservation with GPT-5 Thinking Model")
print(f"Thread: {thread_id}")
print("="*60)

messages = [
    "Find the Breville Bambino Plus espresso machine",
    "What's its price?",
    "Is it in stock?"
]

for i, msg in enumerate(messages, 1):
    print(f"\n[Turn {i}] 📝 {msg}")
    print(f"⏱️  Start: {time.strftime('%H:%M:%S')}")
    
    start_time = time.time()
    
    try:
        if i == 1:
            print("🔍 First query - will search for product...")
        else:
            print("💭 Should use context from previous turn...")
            
        response = requests.post(url, json={
            "message": msg,
            "thread_id": thread_id
        }, timeout=120)
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get('response', 'No response')
            
            print(f"✅ Response in {elapsed:.1f}s")
            print(f"📬 {response_text[:200]}..." if len(response_text) > 200 else f"📬 {response_text}")
            
            # Timing analysis
            if i > 1 and elapsed < 30:
                print(f"⚡ Fast response! Likely used compressed context")
            elif elapsed > 40:
                print(f"🐢 Slow response - probably called agent(s)")
        else:
            print(f"❌ Error {response.status_code} after {elapsed:.1f}s")
            
        time.sleep(2)  # Brief pause between messages
        
    except requests.Timeout:
        print(f"⏱️  Timeout after 120 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n\n📊 Summary:")
print(f"• Thread ID: {thread_id}")
print(f"• Check compression: grep 'Compressed context' server.log | grep '{thread_id}'")
print(f"• Check planning: grep 'Has compressed context' server.log | grep '{thread_id}'")
print(f"• LangSmith: https://smith.langchain.com (search for {thread_id})")