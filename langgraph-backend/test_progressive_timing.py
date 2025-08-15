#!/usr/bin/env python3
"""Test progressive orchestrator with detailed timing for GPT-5 thinking model"""
import requests
import json
import time

url = "http://localhost:8000/api/agent/message"
thread_id = f"timing_test_{int(time.time())}"

print(f"Testing Progressive Orchestrator with GPT-5 Thinking Model")
print(f"URL: {url}")
print(f"Thread: {thread_id}")
print(f"Timeout: 120 seconds (for thinking model)")
print("="*60)

# Single test message
message = "What is the price of Profitec GO?"

print(f"\n📝 Message: {message}")
print(f"⏱️  Start time: {time.strftime('%H:%M:%S')}")

start_time = time.time()

try:
    print("🤔 GPT-5 is thinking...")
    response = requests.post(url, json={
        "message": message,
        "thread_id": thread_id
    }, timeout=120)
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        data = response.json()
        response_text = data.get('response', 'No response')
        
        print(f"✅ Success after {elapsed:.1f} seconds")
        print(f"⏱️  End time: {time.strftime('%H:%M:%S')}")
        print(f"\n📬 Response ({len(response_text)} chars):")
        print(response_text[:500] + "..." if len(response_text) > 500 else response_text)
        
        # Breakdown
        print(f"\n📊 Timing Breakdown:")
        print(f"  • Total time: {elapsed:.1f} seconds")
        if elapsed > 30:
            print(f"  • This is expected for GPT-5 thinking model")
            print(f"  • Includes: planning + agent calls + synthesis")
    else:
        print(f"❌ Error {response.status_code} after {elapsed:.1f} seconds")
        print(response.text)
        
except requests.Timeout:
    elapsed = time.time() - start_time
    print(f"⏱️  Timeout after {elapsed:.1f} seconds")
    print("Consider increasing timeout further for GPT-5 thinking model")
except Exception as e:
    elapsed = time.time() - start_time
    print(f"❌ Error after {elapsed:.1f} seconds: {e}")

print(f"\n🔍 Check logs: grep '{thread_id}' server.log")
print(f"📈 LangSmith: https://smith.langchain.com (search for {thread_id})")