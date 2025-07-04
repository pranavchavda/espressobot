"""
MCP wrapper for search_products tool
"""

from typing import Dict, Any, Optional, List
import sys
import os
import json

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class SearchProductsTool(BaseMCPTool):
    """Search products with advanced filtering"""
    
    name = "search_products"
    description = "Search Shopify products with various filters and options"
    context = """
    Powerful product search with multiple filter options:
    - Search by title, SKU, vendor, product type
    - Filter by status (active, draft, archived)
    - Filter by inventory (in_stock, out_of_stock)
    - Sort results by various fields
    - Limit number of results
    
    Examples:
    - Search for all coffee products: query="coffee"
    - Active products only: query="coffee", status="active"
    - Out of stock items: inventory="out_of_stock"
    - By vendor: vendor="Sanremo"
    
    Returns list of products with basic details.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (searches title, vendor, type, SKU)"
            },
            "status": {
                "type": "string",
                "enum": ["active", "draft", "archived"],
                "description": "Product status filter"
            },
            "vendor": {
                "type": "string",
                "description": "Filter by vendor name"
            },
            "product_type": {
                "type": "string",
                "description": "Filter by product type"
            },
            "inventory": {
                "type": "string",
                "enum": ["in_stock", "out_of_stock"],
                "description": "Filter by inventory status"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results (default: 50)"
            }
        },
        "required": ["query"]
    }
    
    async def execute(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Execute product search natively"""
        import sys
        print(f"[SearchProductsTool] Searching for: {query} with kwargs: {kwargs}", file=sys.stderr)
        try:
            client = ShopifyClient()
            
            # Build search query
            search_query = self._build_search_query(query, **kwargs)
            limit = kwargs.get("limit", 50)
            print(f"[SearchProductsTool] Built search query: {search_query}", file=sys.stderr)
            
            # GraphQL query
            graphql_query = f'''
            query searchProducts($query: String!, $first: Int!) {{
                products(first: $first, query: $query) {{
                    edges {{
                        node {{
                            id
                            title
                            handle
                            vendor
                            productType
                            status
                            tags
                            createdAt
                            updatedAt
                            featuredImage {{
                                url
                                altText
                            }}
                            variants(first: 5) {{
                                edges {{
                                    node {{
                                        id
                                        sku
                                        price
                                        compareAtPrice
                                        availableForSale
                                        inventoryQuantity
                                    }}
                                }}
                            }}
                        }}
                    }}
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                }}
            }}
            '''
            
            variables = {
                "query": search_query,
                "first": min(limit, 250)  # Shopify API limit
            }
            
            result = client.execute_graphql(graphql_query, variables)
            
            print(f"[SearchProductsTool] GraphQL result: {json.dumps(result, indent=2)}", file=sys.stderr)
            
            # Format results
            products = []
            for edge in result.get('data', {}).get('products', {}).get('edges', []):
                product = edge['node']
                products.append(self._format_search_result(product))
            
            print(f"[SearchProductsTool] Found {len(products)} products", file=sys.stderr)
            return products
            
        except Exception as e:
            raise Exception(f"Search failed: {str(e)}")
    
    def _build_search_query(self, query: str, **kwargs) -> str:
        """Build Shopify search query string"""
        filters = []
        
        # Add base query - use wildcards for better matching
        if query:
            # Use wildcards for partial matching
            filters.append(f'title:*{query}* OR vendor:*{query}* OR product_type:*{query}* OR handle:*{query}*')
        
        # Add status filter
        if kwargs.get("status"):
            filters.append(f'status:{kwargs["status"]}')
        
        # Add vendor filter
        if kwargs.get("vendor"):
            filters.append(f'vendor:"{kwargs["vendor"]}"')
        
        # Add product type filter
        if kwargs.get("product_type"):
            filters.append(f'product_type:"{kwargs["product_type"]}"')
        
        # Add inventory filter
        if kwargs.get("inventory"):
            if kwargs["inventory"] == "in_stock":
                filters.append("inventory_total:>0")
            elif kwargs["inventory"] == "out_of_stock":
                filters.append("inventory_total:0")
        
        return " AND ".join(filters) if filters else "*"
    
    def _format_search_result(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Format product for search results"""
        # Get first variant info
        variants = product.get('variants', {}).get('edges', [])
        first_variant = variants[0]['node'] if variants else {}
        
        # Calculate inventory total
        inventory_total = sum(
            variant['node'].get('inventoryQuantity', 0) or 0
            for variant in variants
        )
        
        return {
            'id': product['id'],
            'title': product['title'],
            'handle': product['handle'],
            'vendor': product['vendor'],
            'productType': product['productType'],
            'status': product['status'],
            'tags': product['tags'],
            'featuredImage': product.get('featuredImage'),
            'variantId': first_variant.get('id'),  # Added variant ID
            'price': first_variant.get('price'),
            'compareAtPrice': first_variant.get('compareAtPrice'),  # Added compare at price
            'sku': first_variant.get('sku'),
            'available': first_variant.get('availableForSale', False),
            'inventory_total': inventory_total,
            'variant_count': len(variants),
            'createdAt': product['createdAt'],
            'updatedAt': product['updatedAt']
        }
            
    async def test(self) -> Dict[str, Any]:
        """Test the search tool"""
        try:
            self.validate_env()
            client = ShopifyClient()
            
            # Test with a simple query to verify connection
            result = client.execute_graphql('{ shop { name } }')
            
            return {
                "status": "passed",
                "message": f"Connected to shop: {result.get('data', {}).get('shop', {}).get('name', 'Unknown')}"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }