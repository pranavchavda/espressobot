#!/usr/bin/env python3
"""Test what the orchestrator should do when price isn't in context"""

import asyncio
import logging
import json
from app.context_manager.compressed_context_simple import CompressedContextManager
from langchain_core.messages import HumanMessage, AIMessage

# Set up minimal logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def test_orchestrator_decision_flow():
    # Initialize the context manager
    context_manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # Initial conversation - NO PRICE INFO
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

Yes, the Profitec GO is available in yellow! There's currently 1 unit in stock."""),
        
        # User asks for price - NOT in context
        HumanMessage(content="what's the cost of the item?"),
    ]
    
    print("\n" + "="*80)
    print("ORCHESTRATOR DECISION FLOW TEST")
    print("="*80 + "\n")
    
    # Compress the conversation
    compressed = await context_manager.compress_turn(
        thread_id="orchestrator-flow-test",
        messages=messages
    )
    
    if compressed:
        print("📊 CURRENT CONTEXT")
        print("-" * 40)
        print(f"• Extracted: {compressed.extraction_count} items")
        print(f"• Categories: {', '.join(compressed.extraction_classes)}\n")
        
        # Check what's in context
        has_product = False
        has_price = False
        product_id = None
        variant_id = None
        
        for class_name in compressed.extraction_classes:
            items = compressed.extractions.get(class_name, [])
            for item in items:
                attrs = item.get('attributes', {})
                text = item.get('text', '')
                
                # Look for product info
                if 'product_id' in str(attrs):
                    has_product = True
                    product_id = attrs.get('product_id')
                if 'variant_id' in str(attrs):
                    variant_id = attrs.get('variant_id')
                    
                # Look for price info
                if 'price' in str(attrs).lower() or '$' in text:
                    # But NOT in the question itself
                    if 'cost of the item' not in text:
                        has_price = True
        
        print("🔍 CONTEXT ANALYSIS")
        print("-" * 40)
        print(f"✓ Has product info: {has_product}")
        if product_id:
            print(f"  - Product ID: {product_id}")
        if variant_id:
            print(f"  - Yellow variant ID: gid://shopify/ProductVariant/42345678901237")
        print(f"✗ Has price info: {has_price}")
        
        print("\n💡 ORCHESTRATOR DECISION")
        print("-" * 40)
        print("User asked: 'what's the cost of the item?'\n")
        
        print("WHAT SHOULD HAPPEN:")
        print("1. Orchestrator checks context - finds NO price info")
        print("2. Orchestrator identifies we're discussing Profitec GO (yellow variant)")
        print("3. Orchestrator calls products agent with:")
        print("   → 'Get pricing for Profitec GO yellow variant'")
        print("   → Or uses variant ID: gid://shopify/ProductVariant/42345678901237")
        print("4. Products agent fetches REAL price from Shopify")
        print("5. Orchestrator receives actual price and responds to user\n")
        
        print("❌ WHAT NOT TO DO:")
        print("- Don't make up a price")
        print("- Don't say 'I don't know' when we can fetch it")
        print("- Don't lose track of which product we're discussing")
        
        print("\n" + "="*80)
        print("SIMULATING CORRECT AGENT CALL")
        print("="*80 + "\n")
        
        print("📞 ORCHESTRATOR → PRODUCTS AGENT")
        print("-" * 40)
        print("Request: Get price for Profitec GO (variant: gid://shopify/ProductVariant/42345678901237)")
        print("\n🔄 PRODUCTS AGENT → SHOPIFY API")
        print("-" * 40)
        print("Fetching actual price from Shopify...")
        print("(This would be the REAL price, not made up)")
        
        # What the real response should look like
        print("\n✅ CORRECT FLOW RESULT")
        print("-" * 40)
        print("After agent returns ACTUAL price from Shopify:")
        print("- User gets real price (e.g., $2,195.00 or whatever it actually is)")
        print("- Context is updated with pricing info")
        print("- Future questions about price can be answered from context")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_decision_flow())