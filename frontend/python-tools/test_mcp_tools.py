#!/usr/bin/env python3
"""
Test script for MCP tools
Tests the 5 core tools: get_product, search_products, create_product, update_pricing, manage_inventory_policy
"""
import json
import sys
import os
import asyncio
from typing import Dict, Any

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import MCP tools
from mcp_tools.products.get import GetProductTool
from mcp_tools.products.search import SearchProductsTool
from mcp_tools.products.create import CreateProductTool
from mcp_tools.pricing.update import UpdatePricingTool
from mcp_tools.inventory.manage_policy import ManageInventoryPolicyTool

class MCPToolTester:
    def __init__(self):
        self.tools = {
            "get_product": GetProductTool(),
            "search_products": SearchProductsTool(),
            "create_product": CreateProductTool(),
            "update_pricing": UpdatePricingTool(),
            "manage_inventory_policy": ManageInventoryPolicyTool()
        }
        self.test_results = {}
    
    async def run_all_tests(self):
        """Run all MCP tool tests"""
        print("=" * 60)
        print("MCP TOOLS TEST SUITE")
        print("=" * 60)
        
        for tool_name, tool in self.tools.items():
            print(f"\n🔧 Testing {tool_name}...")
            try:
                result = await self.test_tool(tool_name, tool)
                self.test_results[tool_name] = result
                status = "✅ PASSED" if result["status"] == "passed" else "❌ FAILED"
                print(f"{status}: {result.get('message', result.get('error', 'Unknown'))}")
            except Exception as e:
                self.test_results[tool_name] = {"status": "failed", "error": str(e)}
                print(f"❌ FAILED: {str(e)}")
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results.values() if r["status"] == "passed")
        failed = sum(1 for r in self.test_results.values() if r["status"] == "failed")
        
        print(f"Total tests: {len(self.test_results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        
        if failed > 0:
            print("\nFailed tests:")
            for tool_name, result in self.test_results.items():
                if result["status"] == "failed":
                    print(f"  - {tool_name}: {result.get('error', 'Unknown error')}")
        
        return self.test_results
    
    async def test_tool(self, tool_name: str, tool) -> Dict[str, Any]:
        """Test a specific MCP tool"""
        
        if tool_name == "get_product":
            return await self.test_get_product(tool)
        elif tool_name == "search_products":
            return await self.test_search_products(tool)
        elif tool_name == "create_product":
            return await self.test_create_product(tool)
        elif tool_name == "update_pricing":
            return await self.test_update_pricing(tool)
        elif tool_name == "manage_inventory_policy":
            return await self.test_manage_inventory_policy(tool)
        else:
            return {"status": "failed", "error": f"Unknown tool: {tool_name}"}
    
    async def test_get_product(self, tool) -> Dict[str, Any]:
        """Test get_product tool"""
        try:
            # Test with a common coffee SKU
            result = await tool.execute(identifier="ESP-1001")
            
            if result.get("success"):
                product = result.get("product", {})
                if product.get("title") and product.get("variants"):
                    return {
                        "status": "passed",
                        "message": f"Successfully retrieved product: {product['title']} with {len(product['variants'])} variants"
                    }
                else:
                    return {
                        "status": "failed",
                        "error": "Product retrieved but missing expected fields"
                    }
            else:
                # Try with a search first to find a real product
                search_tool = SearchProductsTool()
                search_result = await search_tool.execute(query="coffee", limit=1)
                
                if search_result and len(search_result) > 0:
                    test_sku = search_result[0].get("sku")
                    if test_sku:
                        result = await tool.execute(identifier=test_sku)
                        if result.get("success"):
                            product = result.get("product", {})
                            return {
                                "status": "passed",
                                "message": f"Successfully retrieved product: {product.get('title', 'Unknown')}"
                            }
                
                return {
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                }
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def test_search_products(self, tool) -> Dict[str, Any]:
        """Test search_products tool"""
        try:
            # Test with a common search term
            result = await tool.execute(query="coffee")
            
            if isinstance(result, list) and len(result) > 0:
                first_product = result[0]
                if first_product.get("title") and first_product.get("handle"):
                    return {
                        "status": "passed",
                        "message": f"Found {len(result)} products. First: {first_product['title']}"
                    }
                else:
                    return {
                        "status": "failed",
                        "error": "Search returned products but missing expected fields"
                    }
            else:
                return {
                    "status": "failed",
                    "error": "Search returned no results"
                }
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def test_create_product(self, tool) -> Dict[str, Any]:
        """Test create_product tool with dry run"""
        try:
            # Create a test product (it will be created as DRAFT)
            result = await tool.execute(
                title="MCP Test Product",
                vendor="Test Vendor",
                product_type="Test",
                description="Test product created by MCP tool test",
                status="DRAFT",
                price=99.99,
                sku=f"MCP-TEST-{int(asyncio.get_event_loop().time())}"
            )
            
            if result.get("success"):
                return {
                    "status": "passed",
                    "message": f"Successfully created test product: {result.get('title')} (ID: {result.get('product_id')})"
                }
            else:
                return {
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                }
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def test_update_pricing(self, tool) -> Dict[str, Any]:
        """Test update_pricing tool"""
        try:
            # First find a product to test pricing on
            search_tool = SearchProductsTool()
            search_result = await search_tool.execute(query="coffee", limit=1)
            
            if not search_result or len(search_result) == 0:
                return {
                    "status": "failed",
                    "error": "No products found for pricing test"
                }
            
            product = search_result[0]
            variant_id = product.get("variantId")
            product_id = product.get("id")
            
            if not variant_id or not product_id:
                return {
                    "status": "failed",
                    "error": "Product found but missing variant or product ID"
                }
            
            # Test with current price (no actual change)
            current_price = float(product.get("price", "0"))
            
            result = await tool.execute(
                product_id=product_id,
                variant_id=variant_id,
                price=current_price
            )
            
            if result.get("success"):
                return {
                    "status": "passed",
                    "message": f"Successfully updated pricing for {product.get('title', 'Unknown')}"
                }
            else:
                return {
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                }
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def test_manage_inventory_policy(self, tool) -> Dict[str, Any]:
        """Test manage_inventory_policy tool"""
        try:
            # First find a product to test policy on
            search_tool = SearchProductsTool()
            search_result = await search_tool.execute(query="coffee", limit=1)
            
            if not search_result or len(search_result) == 0:
                return {
                    "status": "failed",
                    "error": "No products found for inventory policy test"
                }
            
            product = search_result[0]
            variant_id = product.get("variantId")
            
            if not variant_id:
                return {
                    "status": "failed",
                    "error": "Product found but missing variant ID"
                }
            
            # Test setting policy to deny (safe default)
            # Try with SKU first as it might be more reliable
            sku = product.get("sku")
            identifier = sku if sku else variant_id
            
            result = await tool.execute(
                identifier=identifier,
                policy="deny"
            )
            
            if result.get("success"):
                return {
                    "status": "passed",
                    "message": f"Successfully updated inventory policy for {product.get('title', 'Unknown')}"
                }
            else:
                return {
                    "status": "failed",
                    "error": result.get("error", "Unknown error")
                }
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}

async def main():
    """Run the MCP tool tests"""
    tester = MCPToolTester()
    results = await tester.run_all_tests()
    
    # Return appropriate exit code
    failed_count = sum(1 for r in results.values() if r["status"] == "failed")
    return 0 if failed_count == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)