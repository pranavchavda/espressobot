#!/usr/bin/env python3
"""Show raw JSON output from LangExtract"""

import asyncio
import logging
import json
from app.context_manager.compressed_context_simple import CompressedContextManager
from langchain_core.messages import HumanMessage, AIMessage

# Set up minimal logging
logging.basicConfig(level=logging.WARNING)

async def show_raw_extraction():
    # Initialize the context manager
    context_manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # Same conversation as before
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
    ]
    
    print("\n" + "="*80)
    print("RAW LANGEXTRACT JSON OUTPUT")
    print("="*80 + "\n")
    
    # Compress the conversation
    compressed = await context_manager.compress_turn(
        thread_id="raw-json-example",
        messages=messages
    )
    
    if compressed:
        # Show the raw extractions dictionary
        print("📋 RAW EXTRACTIONS DICTIONARY:")
        print("-" * 40)
        
        # Pretty print the entire extractions dictionary
        raw_json = {
            "extraction_count": compressed.extraction_count,
            "extraction_classes": compressed.extraction_classes,
            "extractions": compressed.extractions
        }
        
        print(json.dumps(raw_json, indent=2, default=str))
        
        print("\n" + "="*80)
        print("BREAKDOWN BY EXTRACTION CLASS")
        print("="*80 + "\n")
        
        # Show each extraction class separately for clarity
        for class_name in compressed.extraction_classes:
            print(f"📌 {class_name.upper()}:")
            print("-" * 40)
            items = compressed.extractions.get(class_name, [])
            print(json.dumps(items, indent=2, default=str))
            print()

if __name__ == "__main__":
    asyncio.run(show_raw_extraction())