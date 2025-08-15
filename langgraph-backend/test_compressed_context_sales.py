#!/usr/bin/env python3
"""
Test script for compressed context extraction with sales/analytics data
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

async def test_sales_extraction():
    """Test LangExtract extraction with sales/analytics conversation"""
    
    # Initialize the manager
    manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # Create sample messages for sales analytics
    messages = [
        HumanMessage(content="Check today's sales and website traffic"),
        AIMessage(content="""I'll check today's sales and website traffic for you.

Sales Report for January 13, 2025:
- Total Orders: 127
- Total Revenue: $45,892.50
- Average Order Value: $361.35
- Top Product: Breville Barista Express (12 units sold)

Website Traffic for January 13, 2025:
- Total Sessions: 3,842
- Unique Visitors: 2,156
- Page Views: 15,683
- Conversion Rate: 3.3%
- Bounce Rate: 42.1%

The sales are performing well above average today, with a higher conversion rate than usual.""")
    ]
    
    # Sample agent results (mimicking what agents return)
    agent_results = {
        "sales": """Daily sales summary:
- Orders: 127
- Revenue: $45,892.50
- AOV: $361.35""",
        "ga4_analytics": """Traffic report:
- Sessions: 3,842
- Visitors: 2,156
- Conversion: 3.3%"""
    }
    
    print("Testing compressed context extraction for sales/analytics...")
    print("-" * 50)
    
    # Run the compression
    context = await manager.compress_turn(
        thread_id="test_sales_thread",
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
    for agent, results in context.agent_results.items():
        if results:
            print(f"  - {agent}: {results[0].get('summary', 'N/A')[:100]}")
    
    print(f"\nDecisions: {len(context.decisions)}")
    for decision in context.decisions:
        print(f"  - {decision}")
    
    # Test the context string generation
    context_str = context.to_context_string(max_tokens=500)
    print(f"\nContext string ({len(context_str)} chars):")
    print(context_str)
    
    return context

async def test_image_upload():
    """Test LangExtract extraction with media/image upload conversation"""
    
    # Initialize the manager
    manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # Create sample messages for image upload
    messages = [
        HumanMessage(content="Upload the new lifestyle image to the Mexican Altura product"),
        AIMessage(content="""I'll upload the lifestyle image to the Mexican Altura product.

Finding the product...
Product found: gid://shopify/Product/8456729103
Title: Mexican Altura - Medium Roast Coffee
SKU: COFFEE-MEX-001

Uploading image...
✅ Image uploaded successfully:
- File: lifestyle_coffee_brewing.jpg
- Alt text: "Mexican Altura coffee being brewed in a French press"
- Position: 3 (added as third image)
- Status: READY

The lifestyle image has been successfully added to the Mexican Altura product listing.""")
    ]
    
    # Sample agent results
    agent_results = {
        "media": """Image upload completed:
- Product: gid://shopify/Product/8456729103
- Image: lifestyle_coffee_brewing.jpg
- Position: 3
- Status: Success"""
    }
    
    print("\n" + "=" * 50)
    print("Testing compressed context extraction for image upload...")
    print("-" * 50)
    
    # Run the compression
    context = await manager.compress_turn(
        thread_id="test_media_thread",
        messages=messages,
        agent_results=agent_results
    )
    
    print("\nExtraction Results:")
    print(f"Products found: {len(context.products)}")
    for pid, details in context.products.items():
        print(f"  - {pid}: {details}")
    
    print(f"\nOperations: {len(context.operations)}")
    for op in context.operations:
        print(f"  - Type: {op.get('type')}, Result: {op.get('result')}, Details: {op.get('details', '')[:50]}")
    
    print(f"\nUser goals: {len(context.user_goals)}")
    for goal in context.user_goals:
        print(f"  - {goal}")
    
    return context

if __name__ == "__main__":
    # Test sales extraction
    sales_context = asyncio.run(test_sales_extraction())
    
    # Test image upload extraction
    image_context = asyncio.run(test_image_upload())
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("-" * 50)
    
    # Check sales test
    if sales_context and (sales_context.operations or sales_context.user_goals):
        print("✅ Sales test PASSED - Context extracted successfully")
    else:
        print("❌ Sales test FAILED - No context extracted")
    
    # Check image test  
    if image_context and image_context.products:
        print("✅ Image test PASSED - Product extracted successfully")
    else:
        print("❌ Image test FAILED - No product extracted")