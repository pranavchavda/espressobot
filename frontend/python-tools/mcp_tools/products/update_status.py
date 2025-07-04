"""
MCP wrapper for update_status tool
"""

from typing import Dict, Any, Optional
import json
import subprocess
import os
from ..base import BaseMCPTool

class UpdateStatusTool(BaseMCPTool):
    """Update product status"""
    
    name = "update_status"
    description = "Change product status between active, draft, and archived"
    context = """
    Controls product visibility and availability:
    
    Status options:
    - ACTIVE: Product is visible and available for purchase
    - DRAFT: Product is hidden from storefront (for preparation/review)
    - ARCHIVED: Product is hidden and preserved for records
    
    Important notes:
    - Changing to draft/archived will hide product from customers
    - Archived products cannot be purchased even with direct link
    - Use draft for temporary hiding, archived for permanent removal
    - Status change affects ALL variants of a product
    """
    
    input_schema = {
        "type": "object", 
        "properties": {
            "product": {
                "type": "string",
                "description": "Product ID, handle, SKU, or title"
            },
            "status": {
                "type": "string",
                "enum": ["ACTIVE", "DRAFT", "ARCHIVED"],
                "description": "New product status"
            }
        },
        "required": ["product", "status"]
    }
    
    async def execute(self, product: str, status: str) -> Dict[str, Any]:
        """Execute update_status.py tool"""
        self.validate_env()
        
        tool_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "update_status.py"
        )
        
        try:
            result = subprocess.run(
                ["python3", tool_path, "--product", product, "--status", status],
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
            raise Exception(f"update_status failed: {error_msg}")
            
    async def test(self) -> Dict[str, Any]:
        """Test the tool"""
        try:
            tool_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "update_status.py"
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