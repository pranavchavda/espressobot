#!/usr/bin/env python3
"""
Check what's actually being sent to the LLM in the Progressive orchestrator
"""
import asyncio
import tiktoken
from app.orchestrator_progressive import ProgressiveOrchestrator, ConversationMemory
from langchain_core.messages import HumanMessage, AIMessage

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Count tokens in text"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

async def test_token_usage():
    """Test token usage with different scenarios"""
    orchestrator = ProgressiveOrchestrator()
    
    # Scenario 1: Fresh conversation
    print("=" * 80)
    print("SCENARIO 1: Fresh Conversation")
    print("=" * 80)
    
    memory = ConversationMemory()
    memory.add_recent_message(HumanMessage(content="Find Profitec GO"))
    
    # Build what would be sent to planning
    known_context = orchestrator._build_known_context(memory)
    
    recent_conversation = ""
    for msg in memory.recent_messages[-2:]:
        if hasattr(msg, 'content'):
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
            recent_conversation += f"{role}: {content}\n"
    
    planning_prompt = f"""You are an intelligent orchestrator managing specialized agents.

Current user request: Find Profitec GO

{recent_conversation}

What we already know from this conversation:
{known_context}

Available agents:
[... agent list ...]

[... rest of prompt ...]"""
    
    tokens = count_tokens(planning_prompt)
    print(f"Planning prompt tokens: {tokens}")
    print(f"Known context size: {len(known_context)} chars")
    print(f"Recent conversation size: {len(recent_conversation)} chars")
    
    # Scenario 2: After loading history (old way)
    print("\n" + "=" * 80)
    print("SCENARIO 2: With Loaded History (OLD WAY - 20 messages)")
    print("=" * 80)
    
    memory2 = ConversationMemory()
    # Simulate loading 20 messages
    for i in range(10):
        memory2.add_recent_message(HumanMessage(content=f"User message {i} - " + "x" * 500))
        memory2.add_recent_message(AIMessage(content=f"Assistant response {i} - " + "y" * 1000))
    
    # This would keep only last 5 (old) or 3 (new)
    print(f"Messages in memory: {len(memory2.recent_messages)}")
    
    recent_conversation2 = ""
    for msg in memory2.recent_messages[-4:]:  # Old way: last 4 messages
        if hasattr(msg, 'content'):
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            content = msg.content[:500] + "..." if len(msg.content) > 500 else msg.content  # Old truncation
            recent_conversation2 += f"{role}: {content}\n"
    
    tokens2 = count_tokens(recent_conversation2)
    print(f"Recent conversation tokens (old way): {tokens2}")
    print(f"Recent conversation size: {len(recent_conversation2)} chars")
    
    # Scenario 3: With NEW limits
    print("\n" + "=" * 80)
    print("SCENARIO 3: With NEW Limits (3 messages, 300 char truncation)")
    print("=" * 80)
    
    memory3 = ConversationMemory()
    # Load same messages but apply new limits
    for i in range(10):
        memory3.add_recent_message(HumanMessage(content=f"User message {i} - " + "x" * 500))
        memory3.add_recent_message(AIMessage(content=f"Assistant response {i} - " + "y" * 1000))
    
    print(f"Messages in memory (new limit): {len(memory3.recent_messages)}")
    
    recent_conversation3 = ""
    for msg in memory3.recent_messages[-2:]:  # NEW: last 2 messages only
        if hasattr(msg, 'content'):
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content  # NEW: 300 char limit
            recent_conversation3 += f"{role}: {content}\n"
    
    tokens3 = count_tokens(recent_conversation3)
    print(f"Recent conversation tokens (new way): {tokens3}")
    print(f"Recent conversation size: {len(recent_conversation3)} chars")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Token reduction: {tokens2 - tokens3} tokens saved ({(tokens2-tokens3)/tokens2*100:.1f}% reduction)")
    
    # Check what might cause 78K tokens
    print("\n" + "=" * 80)
    print("WHAT COULD CAUSE 78K TOKENS?")
    print("=" * 80)
    
    # Each message pair of 1500 chars is about 400 tokens
    chars_for_78k = 78000 * 4  # Rough estimate: 4 chars per token
    print(f"Estimated characters for 78K tokens: {chars_for_78k:,}")
    print(f"That's roughly {chars_for_78k/1500:.0f} full message exchanges of 1500 chars each")
    print("\nLikely cause: Loading ALL historical messages from DB instead of just recent ones")

if __name__ == "__main__":
    asyncio.run(test_token_usage())