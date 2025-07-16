"""
MCP wrapper for bulk_price_update tool - now a self-contained native tool.
"""

from typing import Dict, Any, Optional, List
from collections import defaultdict
from ..base import BaseMCPTool
from ..base import ShopifyClient

class BulkPriceUpdateTool(BaseMCPTool):
    """Update prices for multiple products at once using native API calls."""

    name = "bulk_price_update"
    description = "Update prices for multiple products from a list"
    context = """
    Efficiently update prices for multiple products in a single operation using native Shopify API calls.

    Accepts a list of price updates, each containing:
    - variant_id: Variant ID (numeric or GID format)
    - price: New price
    - compare_at_price: Optional original/MSRP price

    Note: The tool expects Variant IDs, not SKUs. You can get variant IDs
    from get_product or search_products tools.

    Important:
    - Processes updates in batches for efficiency by grouping variants per product.
    - Reports success/failure for each product.
    - Use for seasonal sales, bulk repricing, etc.
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
        """Execute bulk price update natively."""
        self.validate_env()
        client = ShopifyClient()

        # Group variants by product ID
        product_updates: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        errors = []

        for update in updates:
            variant_id = str(update['variant_id'])
            product_id = await self._get_product_id_for_variant(client, variant_id)

            if not product_id:
                errors.append({"variant_id": variant_id, "error": "Product not found"})
                continue

            variant_gid = f"gid://shopify/ProductVariant/{variant_id}" if not variant_id.startswith('gid://') else variant_id
            
            variant_update = {
                "id": variant_gid,
                "price": str(update["price"])
            }
            if "compare_at_price" in update and update["compare_at_price"] is not None:
                variant_update["compareAtPrice"] = str(update["compare_at_price"])
            else:
                variant_update["compareAtPrice"] = None

            product_updates[product_id].append(variant_update)

    # Execute bulk updates per product
        updated_count = 0
        for product_id, variants in product_updates.items():
            mutation = '''
            mutation updateVariantPricing($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants {
                        id
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            variables = {
                'productId': product_id,
                'variants': variants
            }
            result = client.execute_graphql(mutation, variables)
            data = result.get('data', {}).get('productVariantsBulkUpdate', {})
            user_errors = data.get('userErrors', [])

            if user_errors:
                errors.append({"product_id": product_id, "error": user_errors})
            else:
                updated_count += len(data.get('productVariants', []))

        return {
            "success": len(errors) == 0,
            "total_variants_processed": len(updates),
            "variants_updated": updated_count,
            "errors": errors
        }

    async def _get_product_id_for_variant(self, client: ShopifyClient, variant_id: str) -> Optional[str]:
        """Get the parent product ID for a given variant ID."""
        variant_gid = f"gid://shopify/ProductVariant/{variant_id}" if not variant_id.startswith('gid://') else variant_id

        query = '''
        query getProductFromVariant($id: ID!) {
            productVariant(id: $id) {
                product {
                    id
                }
            }
        }
        '''
        result = client.execute_graphql(query, {"id": variant_gid})
        if result and result.get("data", {}).get("productVariant"):
            return result["data"]["productVariant"]["product"]["id"]
        return None

    async def test(self) -> Dict[str, Any]:
        """Test the tool (read-only test)"""
        try:
            self.validate_env()
            client = ShopifyClient()
            query = "{ shop { name } }"
            result = client.execute_graphql(query)
            if result.get('data', {}).get('shop'):
                return {
                    "status": "passed",
                    "message": f"API connectivity verified for shop: {result['data']['shop']['name']}"
                }
            else:
                return {
                    "status": "failed",
                    "message": "Failed to connect to Shopify API"
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }