#!/usr/bin/env python3
"""Test memory extraction"""
import asyncio
import logging
from app.memory.memory_persistence import MemoryExtractionService
from langchain_core.messages import HumanMessage, AIMessage

logging.basicConfig(level=logging.DEBUG)

async def test():
    service = MemoryExtractionService()
    
    # Check if OpenAI client is initialized
    print(f"OpenAI client: {service.openai_client}")
    
    messages = [
        HumanMessage(content="My name is Pranav and I love Ethiopian coffee"),
        AIMessage(content="Nice to meet you Pranav! Ethiopian coffee is excellent, known for its bright, fruity notes.")
    ]
    
    # Check formatted text
    formatted = service._format_messages_for_extraction(messages)
    print(f"Formatted conversation:\n{formatted}\n")
    
    memories = await service.extract_memories_from_conversation(
        messages=messages,
        user_id="1"
    )
    
    print(f"Extracted {len(memories)} memories:")
    for mem in memories:
        print(f"  - {mem.content} (category: {mem.category}, importance: {mem.importance_score})")

if __name__ == "__main__":
    asyncio.run(test())