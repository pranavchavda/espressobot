"""
MCP wrapper for update_pricing tool
"""

from typing import Dict, Any, Optional
import json
import subprocess
import os
from ..base import BaseMCPTool

class UpdatePricingTool(BaseMCPTool):
    """Update product variant pricing"""
    
    name = "update_pricing"
    description = "Update product variant pricing including price, compare-at price, and cost"
    context = """
    Updates pricing for products with intelligent handling of discounts:
    
    Price Types:
    - price: The selling price customers pay
    - compare_at_price: Original/MSRP price (shows as strikethrough)
    
    Discount Logic:
    - If compare_at_price > price: Shows as "On Sale" 
    - If compare_at_price = null: No discount shown
    - To remove discount: Set price = compare_at_price, then clear compare_at_price
    
    IMPORTANT Business Rules:
    - Always preserve original price in compare_at_price before discounting
    - For MAP pricing: Use compare_at_price for MSRP, price for selling price
    - Price changes apply to ALL variants of a product
    - Prices should be in store's currency (USD for iDrinkCoffee)
    
    Examples:
    - Regular price update: --price 49.99
    - Add discount: --price 39.99 --compare-at-price 49.99
    - Remove discount: --price 49.99 --compare-at-price null
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "product_id": {
                "type": "string",
                "description": "Product ID (numeric or GID format)"
            },
            "variant_id": {
                "type": "string",
                "description": "Variant ID to update"
            },
            "price": {
                "type": "number",
                "description": "New selling price"
            },
            "compare_at_price": {
                "type": ["number", "null"],
                "description": "Original/MSRP price (null to remove)"
            },
            "cost": {
                "type": ["number", "null"],
                "description": "Unit cost for inventory tracking"
            }
        },
        "required": ["product_id", "variant_id", "price"]
    }
    
    async def execute(self, product_id: str, variant_id: str, price: float, compare_at_price: Optional[float] = None, cost: Optional[float] = None) -> Dict[str, Any]:
        """Execute update_pricing.py tool"""
        self.validate_env()
        
        tool_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "update_pricing.py"
        )
        
        cmd = ["python3", tool_path, "--product-id", product_id, "--variant-id", variant_id, "--price", str(price)]
        
        if compare_at_price is not None:
            cmd.extend(["--compare-at", str(compare_at_price)])
            
        if cost is not None:
            cmd.extend(["--cost", str(cost)])
            
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output
            output = result.stdout.strip()
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                return {"success": True, "message": output}
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or str(e)
            raise Exception(f"update_pricing failed: {error_msg}")
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool"""
        try:
            # Check if tool is accessible
            tool_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "update_pricing.py"
            )
            
            result = subprocess.run(
                ["python3", tool_path, "--help"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    "status": "passed",
                    "message": "Tool is accessible"
                }
            else:
                return {
                    "status": "failed",
                    "message": "Tool failed to respond"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }