#!/usr/bin/env python3
"""Test context understanding - Profitec GO yellow availability and cost follow-up"""

import asyncio
import logging
import json
from app.context_manager.compressed_context_simple import CompressedContextManager
from langchain_core.messages import HumanMessage, AIMessage

# Set up minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def test_profitec_context():
    # Initialize the context manager
    context_manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # Create conversation about Profitec GO
    messages = [
        HumanMessage(content="is Profitec go available in yellow?"),
        AIMessage(content="""I found the Profitec GO espresso machine, and here's the availability information:

**Profitec GO Espresso Machine**
- Product ID: gid://shopify/Product/7823456789012
- Handle: profitec-go-espresso-machine
- SKU: PROF-GO-2024

**Available Colors:**
1. **Black** - In stock (4 units)
   - Variant ID: gid://shopify/ProductVariant/42345678901234
   
2. **Stainless Steel** - In stock (2 units)  
   - Variant ID: gid://shopify/ProductVariant/42345678901235
   
3. **White** - Out of stock
   - Variant ID: gid://shopify/ProductVariant/42345678901236
   
4. **Yellow** - In stock (1 unit) ✅
   - Variant ID: gid://shopify/ProductVariant/42345678901237
   - Limited edition color
   - Same specifications as other colors

Yes, the Profitec GO is available in yellow! There's currently 1 unit in stock. This is a limited edition color option with the same high-quality specifications as the standard colors:
- Single boiler with PID temperature control
- 58mm commercial portafilter
- Vibration pump
- 2.8L water tank capacity"""),
        
        # Follow-up without naming the product
        HumanMessage(content="what's the cost of the item?"),
    ]
    
    print("\n" + "="*80)
    print("TESTING PROFITEC GO CONTEXT UNDERSTANDING")
    print("="*80 + "\n")
    
    # Compress the conversation
    compressed = await context_manager.compress_turn(
        thread_id="profitec-test",
        messages=messages
    )
    
    if compressed:
        print("📊 EXTRACTION RESULTS")
        print("-" * 40)
        print(f"• Extracted: {compressed.extraction_count} items")
        print(f"• Categories: {len(compressed.extraction_classes)}")
        print(f"• Classes: {', '.join(compressed.extraction_classes)}\n")
        
        print("📝 CONTEXT STRING FOR ORCHESTRATOR")
        print("-" * 40)
        context_str = compressed.to_context_string()
        print(context_str)
        
        print("\n🔍 CHECKING WHAT INFORMATION IS AVAILABLE")
        print("-" * 40)
        
        # Check for product information
        has_product_info = False
        has_price_info = False
        product_name = None
        
        for class_name in compressed.extraction_classes:
            items = compressed.extractions.get(class_name, [])
            for item in items:
                attrs = item.get('attributes', {})
                text = item.get('text', '')
                
                # Check for product identification
                if 'Profitec GO' in text or 'PROF-GO' in str(attrs):
                    has_product_info = True
                    product_name = "Profitec GO"
                    print(f"  ✓ Found product info in '{class_name}': Profitec GO")
                
                # Check for price/cost information
                if 'price' in str(attrs).lower() or 'cost' in str(attrs).lower() or '$' in text:
                    has_price_info = True
                    print(f"  ✓ Found price info in '{class_name}'")
        
        print(f"\n💡 ORCHESTRATOR DECISION FOR 'what's the cost of the item?':")
        print("-" * 40)
        
        if has_price_info:
            print("❌ WOULD NOT CALL AGENT - Price info already in context")
            print("   The orchestrator can answer directly from context")
        elif has_product_info:
            print("✅ WOULD CALL AGENT - Has product info but no price")
            print(f"   Context shows we're discussing: {product_name}")
            print("   The orchestrator knows to fetch price for Profitec GO (from context)")
            print("   Should call products agent with: 'get price for Profitec GO'")
        else:
            print("⚠️  AMBIGUOUS - No clear product reference")
            print("   The orchestrator might be confused about which item")
        
        # Simulate agent response with price
        print("\n" + "="*80)
        print("SIMULATING AGENT RESPONSE WITH PRICE")
        print("="*80 + "\n")
        
        messages.append(AIMessage(content="""The Profitec GO pricing details:

**Price:** $1,695.00
**Compare at Price:** $1,895.00
**Savings:** $200 (10.5% off)

The yellow edition is priced the same as other colors. This includes:
- Free shipping (orders over $500)
- 2-year manufacturer warranty
- Optional extended warranty available for $149

Would you like me to add the yellow Profitec GO to your cart?"""))
        
        messages.append(HumanMessage(content="is it heavier than the standard model?"))
        
        # Compress again with price info
        compressed2 = await context_manager.compress_turn(
            thread_id="profitec-test",
            messages=messages
        )
        
        print("📊 UPDATED EXTRACTION RESULTS")
        print("-" * 40)
        print(f"• Total items: {compressed2.extraction_count}")
        print(f"• Categories: {len(compressed2.extraction_classes)}")
        
        print("\n💡 CONTEXT TEST: 'is it heavier than the standard model?'")
        print("-" * 40)
        print("The orchestrator should understand:")
        print("  1. 'it' refers to the Profitec GO (specifically yellow)")
        print("  2. 'standard model' likely means other color variants")
        print("  3. Weight info not in context → needs to call agent")
        print("\nExpected orchestrator action:")
        print("  → Call products agent: 'get weight specifications for Profitec GO variants'")
        
        # Save raw JSON
        print("\n" + "="*80)
        print("SAVING RAW JSON OUTPUT")
        print("="*80 + "\n")
        
        raw_json = {
            "test": "profitec_go_context",
            "metadata": {
                "extraction_count": compressed2.extraction_count,
                "extraction_classes": compressed2.extraction_classes,
                "timestamp": "2025-01-14T15:00:00Z"
            },
            "extractions": compressed2.extractions
        }
        
        with open("profitec_test_output.json", "w") as f:
            json.dump(raw_json, f, indent=2, default=str)
        
        print("✅ Raw JSON saved to profitec_test_output.json")
        
        # Show a sample of what was extracted
        print("\n📌 SAMPLE EXTRACTIONS:")
        print("-" * 40)
        for class_name in list(compressed2.extraction_classes)[:5]:
            items = compressed2.extractions.get(class_name, [])
            if items:
                print(f"\n{class_name}:")
                for item in items[:1]:  # Just first item
                    print(f"  Text: {item['text'][:100]}...")
                    if item.get('attributes'):
                        print(f"  Attrs: {json.dumps(item['attributes'], indent=4)[:200]}...")

if __name__ == "__main__":
    asyncio.run(test_profitec_context())