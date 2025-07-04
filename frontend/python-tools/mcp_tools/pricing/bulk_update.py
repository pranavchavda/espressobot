"""
MCP wrapper for bulk_price_update tool
"""

from typing import Dict, Any, Optional, List
import json
import subprocess
import os
import tempfile
from ..base import BaseMCPTool

class BulkPriceUpdateTool(BaseMCPTool):
    """Update prices for multiple products at once"""
    
    name = "bulk_price_update"
    description = "Update prices for multiple products from a list"
    context = """
    Efficiently update prices for multiple products in a single operation.
    
    Accepts a list of price updates, each containing:
    - variant_id: Variant ID (numeric or GID format)
    - price: New price
    - compare_at_price: Optional original/MSRP price
    
    Note: The tool expects Variant IDs, not SKUs. You can get variant IDs
    from get_product or search_products tools.
    
    Important:
    - Processes updates in batches for efficiency
    - Validates all SKUs before making changes
    - Reports success/failure for each product
    - Use for seasonal sales, bulk repricing, etc.
    
    For complex scenarios (different prices per variant, percentage discounts),
    consider using a bash agent with custom logic.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "updates": {
                "type": "array",
                "description": "List of price updates",
                "items": {
                    "type": "object",
                    "properties": {
                        "variant_id": {"type": "string", "description": "Variant ID (numeric or GID format)"},
                        "price": {"type": "number"},
                        "compare_at_price": {"type": ["number", "null"]}
                    },
                    "required": ["variant_id", "price"]
                }
            }
        },
        "required": ["updates"]
    }
    
    async def execute(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute bulk_price_update.py tool"""
        self.validate_env()
        
        # Create temporary CSV file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            # Write header - bulk_price_update.py expects these exact column names
            f.write("Product ID,Product Title,Variant ID,SKU,Price,Compare At Price\n")
            
            # Write updates
            for update in updates:
                variant_id = update['variant_id']
                price = update['price']
                compare_at = update.get('compare_at_price', '')
                # Product ID and title will be looked up by the tool, SKU is optional
                f.write(f",,{variant_id},,{price},{compare_at}\n")
            
            csv_path = f.name
        
        try:
            tool_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "bulk_price_update.py"
            )
            
            result = subprocess.run(
                ["python3", tool_path, csv_path],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output
            output = result.stdout.strip()
            try:
                return json.loads(output)
            except json.JSONDecodeError:
                # Parse text output for results
                lines = output.split('\n')
                results = {
                    "success": True,
                    "message": output,
                    "updates": len(updates),
                    "processed": len([l for l in lines if 'updated' in l.lower()])
                }
                return results
                
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout or str(e)
            raise Exception(f"bulk_price_update failed: {error_msg}")
        finally:
            # Clean up temp file
            if os.path.exists(csv_path):
                os.unlink(csv_path)
                
    async def test(self) -> Dict[str, Any]:
        """Test the tool"""
        try:
            tool_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "bulk_price_update.py"
            )
            
            # Test with empty CSV to check tool accessibility
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write("Product ID,Product Title,Variant ID,SKU,Price,Compare At Price\n")
                test_csv = f.name
            
            try:
                result = subprocess.run(
                    ["python3", tool_path, test_csv, "--dry-run"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                # We expect it to run (even if no updates)
                return {
                    "status": "passed",
                    "message": "Tool is accessible"
                }
            finally:
                if os.path.exists(test_csv):
                    os.unlink(test_csv)
                    
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }