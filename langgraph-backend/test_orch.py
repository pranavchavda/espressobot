#!/usr/bin/env python3
"""Test orchestrator token usage"""
import asyncio
import aiohttp
import json
import time
from datetime import datetime

async def test_message(message: str, thread_id: str, orchestrator: str = "direct"):
    """Send a single test message"""
    url = "http://localhost:8000/api/chat/message"
    
    payload = {
        "message": message,
        "thread_id": thread_id,
        "use_orchestrator": orchestrator
    }
    
    print(f"\n[{orchestrator.upper()}] Sending: {message}")
    start = time.time()
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status == 200:
                full_response = ""
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if 'content' in chunk:
                                full_response += chunk['content']
                        except:
                            pass
                
                elapsed = time.time() - start
                print(f"Response ({elapsed:.1f}s): {full_response[:150]}...")
                return full_response
            else:
                print(f"Error {response.status}: {await response.text()}")
                return None

async def main():
    """Run comparison test"""
    thread_base = f"test_{int(time.time())}"
    
    # Test both orchestrators with same query
    messages = [
        "What's the price of Profitec GO?",
        "Is it in stock?",
        "What colors are available?"
    ]
    
    # Test with DIRECT orchestrator first
    print("\n" + "="*60)
    print("Testing DIRECT Orchestrator")
    print("="*60)
    
    direct_thread = f"{thread_base}_direct"
    for msg in messages:
        await test_message(msg, direct_thread, "direct")
        await asyncio.sleep(1)
    
    # Test with PROGRESSIVE orchestrator
    print("\n" + "="*60)
    print("Testing PROGRESSIVE Orchestrator")
    print("="*60)
    
    prog_thread = f"{thread_base}_progressive"
    for msg in messages:
        await test_message(msg, prog_thread, "progressive")
        await asyncio.sleep(1)
    
    print("\n" + "="*60)
    print("Test Complete!")
    print(f"Direct thread: {direct_thread}")
    print(f"Progressive thread: {prog_thread}")
    print("\nWait 5 seconds then check LangSmith for traces")
    print("Compare token usage between the two orchestrators")

if __name__ == "__main__":
    asyncio.run(main())