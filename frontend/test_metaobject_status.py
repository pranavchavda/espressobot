#!/usr/bin/env python3
"""Test script for metaobject status functionality"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python_tools.mcp_tools.features.manage_metaobjects import ManageFeaturesMetaobjectsTool

async def test_metaobject_status():
    """Test adding features with different statuses"""
    tool = ManageFeaturesMetaobjectsTool()
    
    # Test product (you'll need to replace with a valid product ID/handle)
    test_product = "mexican-altura"  # Replace with a valid product
    
    print("Testing metaobject status functionality...")
    
    # Test 1: Add feature with ACTIVE status (default)
    print("\n1. Adding feature with ACTIVE status...")
    result = await tool.execute(
        action="add",
        product=test_product,
        title="Active Feature Test",
        description="This feature should be published and visible",
        status="ACTIVE"
    )
    print(f"Result: {result}")
    
    # Test 2: Add feature with DRAFT status
    print("\n2. Adding feature with DRAFT status...")
    result = await tool.execute(
        action="add",
        product=test_product,
        title="Draft Feature Test",
        description="This feature should be hidden in draft mode",
        status="DRAFT"
    )
    print(f"Result: {result}")
    
    # Test 3: List features to verify they were added
    print("\n3. Listing all features...")
    result = await tool.execute(
        action="list",
        product=test_product
    )
    print(f"Result: {result}")
    
    # Test 4: Update a feature to change its status
    if result.get('success') and result.get('features'):
        print("\n4. Updating first feature to DRAFT status...")
        result = await tool.execute(
            action="update",
            product=test_product,
            position=1,
            title="Updated Feature",
            description="Status changed to DRAFT",
            status="DRAFT"
        )
        print(f"Result: {result}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_metaobject_status())