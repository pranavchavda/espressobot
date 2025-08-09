#!/usr/bin/env python
"""Test the memory API endpoints"""
import asyncio
import aiohttp
import json

async def test_memory_api():
    base_url = "http://localhost:8000/api/memory"
    user_id = "1"
    
    async with aiohttp.ClientSession() as session:
        # Test dashboard endpoint
        print("\n1. Testing dashboard endpoint...")
        async with session.get(f"{base_url}/dashboard/{user_id}") as resp:
            print(f"   Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"   Stats: {data.get('stats', {})}")
                print(f"   Recent memories: {len(data.get('recent_memories', []))}")
            else:
                print(f"   Error: {await resp.text()}")
        
        # Test list endpoint
        print("\n2. Testing list endpoint...")
        async with session.get(f"{base_url}/list/{user_id}?limit=10") as resp:
            print(f"   Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"   Found {len(data)} memories")
                if data:
                    print(f"   First memory: {data[0].get('content', '')[:100]}...")
            else:
                print(f"   Error: {await resp.text()}")
        
        # Test search endpoint
        print("\n3. Testing search endpoint...")
        search_body = {
            "query": "coffee",
            "limit": 5,
            "similarity_threshold": 0.5
        }
        async with session.post(
            f"{base_url}/search/{user_id}", 
            json=search_body
        ) as resp:
            print(f"   Status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"   Found {len(data)} matches")
            else:
                print(f"   Error: {await resp.text()}")
        
        print("\n✅ API test complete!")

if __name__ == "__main__":
    asyncio.run(test_memory_api())