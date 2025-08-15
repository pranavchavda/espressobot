#!/usr/bin/env python3
"""
Test script for compressed context extraction
"""
import asyncio
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from app.context_manager.compressed_context import CompressedContextManager
from langchain_core.messages import HumanMessage, AIMessage

async def test_extraction():
    """Test LangExtract extraction with sample conversation"""
    
    # Initialize the manager
    manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # Create sample messages that should contain extractable products
    messages = [
        HumanMessage(content="Find the Breville Barista Express"),
        AIMessage(content="""I found the Breville Barista Express for you:

Product ID: gid://shopify/Product/7923456789
Title: Breville Barista Express BES870XL
SKU: BES870XL
Price: $699.99
Status: ACTIVE

This is a popular semi-automatic espresso machine with built-in grinder.""")
    ]
    
    # Sample agent results (mimicking what agents return)
    agent_results = {
        "products": """Found product:
- ID: gid://shopify/Product/7923456789
- Title: Breville Barista Express BES870XL  
- SKU: BES870XL
- Price: $699.99"""
    }
    
    print("Testing compressed context extraction...")
    print("-" * 50)
    
    # Run the compression
    context = await manager.compress_turn(
        thread_id="test_thread",
        messages=messages,
        agent_results=agent_results
    )
    
    print("\nExtraction Results:")
    print(f"Products found: {len(context.products)}")
    for pid, details in context.products.items():
        print(f"  - {pid}: {details}")
    
    print(f"\nOperations: {len(context.operations)}")
    for op in context.operations:
        print(f"  - {op}")
    
    print(f"\nUser goals: {len(context.user_goals)}")
    for goal in context.user_goals:
        print(f"  - {goal}")
    
    print(f"\nAgent results: {list(context.agent_results.keys())}")
    
    # Test the context string generation
    context_str = context.to_context_string(max_tokens=500)
    print(f"\nContext string ({len(context_str)} chars):")
    print(context_str)
    
    return context

if __name__ == "__main__":
    result = asyncio.run(test_extraction())
    print("\n" + "=" * 50)
    if result and result.products:
        print("✅ Test PASSED - Products were extracted successfully")
    else:
        print("❌ Test FAILED - No products were extracted")