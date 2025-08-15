#!/usr/bin/env python3
"""Test LangExtract extraction with sample product conversation"""

import asyncio
import logging
from app.context_manager.compressed_context import CompressedContextManager
from langchain_core.messages import HumanMessage, AIMessage

# Set up logging to see what's happening  
logging.basicConfig(level=logging.INFO)  # Show extraction details
logger = logging.getLogger(__name__)
logging.getLogger("app.context_manager.compressed_context").setLevel(logging.DEBUG)

async def test_extraction():
    # Initialize the context manager
    context_manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # Create a sample conversation with product details
    messages = [
        HumanMessage(content="Find Sanremo YOU espresso machines"),
        AIMessage(content="""I found 2 Sanremo YOU espresso machines available:

1. **Sanremo YOU Espresso Machine - Black**
   - Product ID: gid://shopify/Product/7199156830242
   - Variant ID: gid://shopify/ProductVariant/41072167878690
   - SKU: SANREMO-YOU-BLACK
   - Price: $9,500.00
   - Compare at: $10,500.00
   - Inventory: 6 units in stock
   - Status: ACTIVE
   - Handle: sanremo-you-espresso-machine

2. **Sanremo YOU Espresso Machine - White**
   - Product ID: gid://shopify/Product/7199158435874
   - Variant ID: gid://shopify/ProductVariant/41072167911458
   - SKU: SANREMO-YOU-WHITE  
   - Price: $9,500.00
   - Compare at: $10,500.00
   - Inventory: 3 units in stock
   - Status: ACTIVE
   - Handle: sanremo-you-espresso-machine-white

Both machines are premium commercial-grade espresso machines with temperature stability and dual boiler systems."""),
        HumanMessage(content="Do they have compare prices set?"),
        AIMessage(content="Looking at the details...")
    ]
    
    # Simulate agent results
    agent_results = {
        "products": """Found 2 products:
- Sanremo YOU - Black: $9,500.00 (compare at $10,500.00)
- Sanremo YOU - White: $9,500.00 (compare at $10,500.00)
Both have compare prices showing a $1,000 discount."""
    }
    
    # Test the extraction
    print("\n" + "="*80)
    print("TESTING LANGEXTRACT EXTRACTION")
    print("="*80 + "\n")
    
    # Compress the conversation
    compressed = await context_manager.compress_turn(
        thread_id="test-extraction",
        messages=messages,
        agent_results=agent_results
    )
    
    if compressed:
        print("✅ EXTRACTION SUCCESSFUL!\n")
        print("-" * 40)
        print("PRODUCTS EXTRACTED:")
        print("-" * 40)
        for product_id, details in compressed.products.items():
            print(f"\nProduct ID: {product_id}")
            for key, value in details.items():
                print(f"  {key}: {value}")
        
        print("\n" + "-" * 40)
        print("OPERATIONS EXTRACTED:")
        print("-" * 40)
        for op in compressed.operations:
            print(f"\n- Type: {op.get('type')}")
            print(f"  Result: {op.get('result')}")
            print(f"  Details: {op.get('details', 'N/A')[:100]}")
        
        print("\n" + "-" * 40)
        print("USER GOALS:")
        print("-" * 40)
        for goal in compressed.user_goals:
            print(f"- {goal}")
        
        print("\n" + "-" * 40)
        print("AGENT RESULTS:")
        print("-" * 40)
        for agent, results in compressed.agent_results.items():
            print(f"\n{agent}:")
            for result in results:
                print(f"  - {result.get('summary', 'N/A')[:100]}")
        
        print("\n" + "-" * 40)
        print("CONTEXT STRING FOR ORCHESTRATOR:")
        print("-" * 40)
        context_string = compressed.to_context_string()
        print(context_string)
        
    else:
        print("❌ No extraction returned!")

if __name__ == "__main__":
    asyncio.run(test_extraction())