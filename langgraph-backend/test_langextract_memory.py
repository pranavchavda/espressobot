#!/usr/bin/env python3
"""Test langextract-based memory extraction"""
import asyncio
import logging
from app.memory.memory_persistence import MemoryExtractionService
from langchain_core.messages import HumanMessage, AIMessage

logging.basicConfig(level=logging.INFO)

async def test():
    service = MemoryExtractionService()
    
    messages = [
        HumanMessage(content="I'm a DevOps engineer at Netflix and I prefer TypeScript over JavaScript for backend work"),
        AIMessage(content="Interesting choice! TypeScript at Netflix for backend - that's great for type safety in your DevOps work.")
    ]
    
    print("Testing langextract memory extraction...")
    memories = await service.extract_memories_from_conversation(
        messages=messages,
        user_id="test_user"
    )
    
    print(f"\nExtracted {len(memories)} memories:")
    for mem in memories:
        print(f"  - {mem.content}")
        print(f"    Category: {mem.category}, Importance: {mem.importance_score}")
        print(f"    Metadata: {mem.metadata}")

if __name__ == "__main__":
    asyncio.run(test())