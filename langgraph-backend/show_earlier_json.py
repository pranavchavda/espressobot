#!/usr/bin/env python3
"""Show raw JSON from the earlier complex conversation test"""

import asyncio
import logging
import json
from app.context_manager.compressed_context_simple import CompressedContextManager
from langchain_core.messages import HumanMessage, AIMessage

# Minimal logging
logging.basicConfig(level=logging.WARNING)

async def show_earlier_test_json():
    context_manager = CompressedContextManager(model_id="gpt-4o-mini")
    
    # The exact conversation from the earlier test
    messages = [
        HumanMessage(content="I need a coffee grinder and an espresso machine for my cafe"),
        AIMessage(content="""I can help you find commercial equipment for your cafe. Here are some excellent options:

**Grinders:**
1. Mahlkonig E65S GBW
   - Price: $2,849.00
   - Grind speed: 4-7g/sec
   - Hopper: 1200g capacity
   - Features: Grind-by-weight technology
   - Stock: 3 units available
   - SKU: MAHL-E65S-GBW

2. Eureka Atom 75
   - Price: $1,395.00  
   - Grind speed: 3.5g/sec
   - Hopper: 1600g capacity
   - Features: Touch display, titanium burrs
   - Stock: 8 units available
   - SKU: EUREKA-ATOM-75

**Espresso Machines:**
1. La Marzocco Linea Mini
   - Price: $5,900.00
   - Boiler: Dual boiler system
   - Group heads: 1
   - Features: PID temperature control, pre-infusion
   - Stock: 2 units available (1 red, 1 black)
   - Product ID: gid://shopify/Product/8234567890123

2. Sanremo YOU
   - Price: $9,500.00 (Compare at: $10,500.00 - SAVE $1,000!)
   - Boiler: Multi-boiler with independent temperature
   - Group heads: 2 available
   - Features: Pressure profiling, shot timer, USB updates
   - Stock: 5 units
   - Product ID: gid://shopify/Product/7199156830242

For a cafe, I'd recommend the Sanremo YOU with the Mahlkonig grinder for high-volume consistency."""),
        
        HumanMessage(content="What about the warranty and shipping on these?"),
        AIMessage(content="""Great questions! Here are the warranty and shipping details:

**Warranty Coverage:**
- Mahlkonig E65S: 2-year manufacturer warranty + optional 3rd year for $299
- Eureka Atom 75: 2-year warranty on parts, 1-year on labor
- La Marzocco Linea Mini: 2-year warranty with registration required within 30 days
- Sanremo YOU: 1-year warranty, extendable to 3 years with certified installation

**Shipping Information:**
- Free shipping on all orders over $5,000 (Sanremo YOU and La Marzocco qualify)
- Grinders ship via FedEx Ground (3-5 business days)
- Espresso machines ship via freight carrier (5-10 business days)
- White glove delivery available for +$350
- All items ship from our Toronto warehouse

**Installation Services:**
- Professional installation available in GTA for $450
- Includes setup, calibration, and barista training (2 hours)
- Required for extended warranty on Sanremo

Would you like me to create a quote bundle with installation included?"""),
        
        HumanMessage(content="Yes, create a bundle with the Sanremo and Mahlkonig, including installation")
    ]
    
    print("\n" + "="*80)
    print("RAW JSON FROM EARLIER CAFE EQUIPMENT TEST")
    print("="*80 + "\n")
    
    compressed = await context_manager.compress_turn(
        thread_id="cafe-equipment",
        messages=messages
    )
    
    if compressed:
        # Create the full JSON structure
        raw_json = {
            "metadata": {
                "extraction_count": compressed.extraction_count,
                "extraction_classes": compressed.extraction_classes,
                "timestamp": "2025-08-14T14:00:00Z"
            },
            "extractions": compressed.extractions
        }
        
        # Pretty print the entire JSON
        print(json.dumps(raw_json, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(show_earlier_test_json())