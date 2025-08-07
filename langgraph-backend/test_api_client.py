#!/usr/bin/env python3
"""
Simple API client to test the LangGraph backend
"""

import asyncio
import aiohttp
import json
import sys

async def test_query(query: str):
    """Send a query and print the response"""
    url = "http://localhost:8000/api/agent/stream"
    
    payload = {
        "message": query,
        "user_id": "1",
        "conversation_id": "test-session"
    }
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            buffer = ""
            async for line in response.content:
                if line:
                    try:
                        # Decode line
                        line_text = line.decode('utf-8').strip()
                        if line_text:
                            # Parse JSON
                            data = json.loads(line_text)
                            
                            # Handle different event types
                            if data.get("event") == "agent_message":
                                agent = data.get("agent", "Unknown")
                                message = data.get("message", "")
                                tokens = data.get("tokens", [])
                                
                                # Update buffer with latest message
                                if message:
                                    buffer = message
                                
                                # Print tokens as they come
                                for token in tokens:
                                    print(token, end="", flush=True)
                            
                            elif data.get("event") == "agent_complete":
                                print(f"\n[Agent: {data.get('agent', 'Unknown')}]")
                            
                            elif data.get("event") == "error":
                                print(f"\n❌ Error: {data.get('message', 'Unknown error')}")
                                break
                            
                            elif data.get("event") == "end":
                                print("\n✅ Complete")
                                break
                                
                    except json.JSONDecodeError:
                        # Not JSON, might be plain text
                        pass
                    except Exception as e:
                        print(f"\nError processing line: {e}")
    
    print()

async def main():
    """Run test queries"""
    
    queries = [
        "Search for Profitec products",
        "Show me espresso machines under $2000",
        "What's the current time?",
    ]
    
    if len(sys.argv) > 1:
        # Use command line argument if provided
        queries = [" ".join(sys.argv[1:])]
    
    for query in queries:
        await test_query(query)
        await asyncio.sleep(1)  # Small delay between queries

if __name__ == "__main__":
    asyncio.run(main())