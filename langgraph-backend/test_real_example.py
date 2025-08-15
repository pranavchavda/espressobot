#!/usr/bin/env python3
"""Real example showing how dynamic extraction handles complex conversations"""

import asyncio
import logging
from app.context_manager.compressed_context_simple import CompressedContextManager
from langchain_core.messages import HumanMessage, AIMessage

# Set up logging to show what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

async def test_real_conversation():
    # Initialize the context manager
    context_manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # Real conversation about Sanremo YOU machines
    messages = [
        HumanMessage(content="find sanremo you"),
        AIMessage(content="""I found 2 Sanremo YOU espresso machines available:

1. **Sanremo YOU Espresso Machine - Black**
   - Product ID: gid://shopify/Product/7199156830242
   - Variant ID: gid://shopify/ProductVariant/41072167878690
   - Handle: sanremo-you-espresso-machine
   - Price: $9,500.00
   - Availability: In stock (6 units)
   - Image: https://cdn.shopify.com/s/files/1/1201/3604/files/YOU_26_0001.jpg?v=1687017890

2. **Sanremo YOU Espresso Machine - White**
   - Product ID: gid://shopify/Product/7199158435874
   - Handle: sanremo-you-espresso-machine-white
   - Status: ACTIVE
   - Price: $9,500.00
   - Availability: In stock (3 units)

Both machines feature professional-grade dual boiler systems with independent temperature control."""),
        
        HumanMessage(content="do they have compare prices set?"),
        
        # This is where we want to test if the orchestrator would need to call an agent
        # or if it can answer from context
    ]
    
    print("\n" + "="*80)
    print("REAL EXAMPLE: Sanremo YOU Product Query")
    print("="*80 + "\n")
    
    # Compress the conversation
    compressed = await context_manager.compress_turn(
        thread_id="real-example",
        messages=messages
    )
    
    if compressed:
        print("📊 EXTRACTION RESULTS")
        print("-" * 40)
        print(f"• Extracted: {compressed.extraction_count} items")
        print(f"• Categories: {len(compressed.extraction_classes)}")
        print(f"• Classes: {', '.join(compressed.extraction_classes)}\n")
        
        # Show the context string the orchestrator would see
        print("📝 CONTEXT FOR ORCHESTRATOR")
        print("-" * 40)
        context_str = compressed.to_context_string()
        print(context_str)
        
        print("\n🔍 ORCHESTRATOR DECISION LOGIC")
        print("-" * 40)
        
        # Check what information is available
        print("Checking if we have pricing information in context...")
        
        # Look for price-related extractions
        has_price_info = False
        has_compare_price = False
        
        for class_name in compressed.extraction_classes:
            items = compressed.extractions.get(class_name, [])
            for item in items:
                attrs = item.get('attributes', {})
                text = item.get('text', '')
                
                # Check if we have price information
                if 'price' in attrs or 'Price:' in text:
                    has_price_info = True
                    print(f"  ✓ Found price in '{class_name}': {attrs.get('price', text[:50])}")
                
                # Check if we have compare price
                if 'compare' in str(attrs).lower() or 'compare' in text.lower():
                    has_compare_price = True
                    print(f"  ✓ Found compare price mention in '{class_name}'")
        
        print(f"\nPrice information available: {has_price_info}")
        print(f"Compare price information available: {has_compare_price}")
        
        print("\n💡 ORCHESTRATOR DECISION:")
        print("-" * 40)
        
        if has_compare_price:
            print("❌ WOULD NOT CALL AGENT - Compare price info already in context")
            print("   The orchestrator can answer directly from context")
        elif has_price_info:
            print("⚠️  MIGHT CALL AGENT - Has price but no compare price info")
            print("   The orchestrator should call products agent to check compare prices")
        else:
            print("✅ WOULD CALL AGENT - No pricing information in context")
            print("   The orchestrator needs to call products agent for pricing details")
        
        # Now simulate adding the compare price info
        print("\n" + "="*80)
        print("SIMULATING FOLLOW-UP WITH COMPARE PRICES")
        print("="*80 + "\n")
        
        # Add the response with compare prices
        messages.append(AIMessage(content="""Yes, both Sanremo YOU machines have compare-at prices set:

1. **Sanremo YOU - Black**
   - Regular Price: $9,500.00
   - Compare At Price: $10,500.00
   - Savings: $1,000 (9.5% off)

2. **Sanremo YOU - White**  
   - Regular Price: $9,500.00
   - Compare At Price: $10,500.00
   - Savings: $1,000 (9.5% off)

The compare-at price represents the manufacturer's suggested retail price (MSRP)."""))
        
        messages.append(HumanMessage(content="what's the inventory on these?"))
        
        # Compress again with the additional context
        compressed2 = await context_manager.compress_turn(
            thread_id="real-example",
            messages=messages
        )
        
        print("📊 UPDATED EXTRACTION RESULTS")
        print("-" * 40)
        print(f"• Total items: {compressed2.extraction_count}")
        print(f"• Categories: {len(compressed2.extraction_classes)}")
        
        print("\n🔍 CHECKING FOR INVENTORY INFO")
        print("-" * 40)
        
        has_inventory = False
        for class_name in compressed2.extraction_classes:
            items = compressed2.extractions.get(class_name, [])
            for item in items:
                attrs = item.get('attributes', {})
                text = item.get('text', '')
                
                if 'inventory' in str(attrs).lower() or 'stock' in text.lower() or 'units' in text.lower():
                    has_inventory = True
                    print(f"  ✓ Found inventory in '{class_name}': {text[:80]}")
        
        print(f"\n💡 ORCHESTRATOR DECISION FOR 'what's the inventory on these?':")
        print("-" * 40)
        if has_inventory:
            print("❌ WOULD NOT CALL AGENT - Inventory info already in context")
            print("   Can answer: Black has 6 units, White has 3 units")
        else:
            print("✅ WOULD CALL AGENT - Need to fetch current inventory levels")

if __name__ == "__main__":
    asyncio.run(test_real_conversation())