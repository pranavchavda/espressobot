"""
MCP wrapper for manage_inventory_policy tool
"""

from typing import Dict, Any, Optional
import json
import subprocess
import os
from ..base import BaseMCPTool

class ManageInventoryPolicyTool(BaseMCPTool):
    """Manage product inventory policy (oversell settings)"""
    
    name = "manage_inventory_policy"
    description = "Set inventory policy to control whether products can be oversold"
    context = """
    Controls whether customers can purchase when inventory reaches zero:
    
    - DENY (default): Prevents overselling - customers cannot buy when out of stock
      Use for: Physical inventory, limited stock items
      
    - ALLOW/CONTINUE: Allows overselling - customers can buy even when out of stock  
      Use for: Pre-orders, made-to-order items, digital products
      
    IMPORTANT: 
    - This applies to ALL variants of a product
    - Check current inventory levels before changing policy
    - For pre-orders, use ALLOW with clear messaging in product description
    
    Accepts identifiers:
    - Variant ID (e.g., "31480448974882" or "gid://shopify/ProductVariant/31480448974882")
    - SKU (e.g., "ESP-1001")
    - Product handle (e.g., "mexican-altura")
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "identifier": {
                "type": "string",
                "description": "Variant ID, SKU, or product handle"
            },
            "policy": {
                "type": "string",
                "enum": ["deny", "allow", "continue"],
                "description": "Inventory policy (deny=no oversell, allow/continue=oversell allowed)"
            }
        },
        "required": ["identifier", "policy"]
    }
    
    async def execute(self, identifier: str, policy: str) -> Dict[str, Any]:
        """Execute manage_inventory_policy.py tool"""
        self.validate_env()
        
        # Normalize policy value
        policy = policy.lower()
        if policy == "continue":
            policy = "allow"  # Handle both naming conventions
            
        tool_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "manage_inventory_policy.py"
        )
        
        try:
            result = subprocess.run(
                ["python3", tool_path, "--identifier", identifier, "--policy", policy],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output - the tool may return text or JSON
            output = result.stdout.strip()
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # If not JSON, return as message
                return {"success": True, "message": output}
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or str(e)
            raise Exception(f"manage_inventory_policy failed: {error_msg}")
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool (read-only test)"""
        try:
            # We can't actually change policies in test, so just verify the tool loads
            # Check if we can at least call the tool with --help
            tool_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "manage_inventory_policy.py"
            )
            
            result = subprocess.run(
                ["python3", tool_path, "--help"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    "status": "passed",
                    "message": "Tool is accessible and responds to --help"
                }
            else:
                return {
                    "status": "failed",
                    "message": "Tool failed to respond to --help"
                }
                
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }