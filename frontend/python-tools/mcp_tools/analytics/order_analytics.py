"""
Order analytics tool for Shopify - handles high-volume order data
"""

from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta
from ..base import BaseMCPTool, ShopifyClient

class OrderAnalyticsTool(BaseMCPTool):
    """Get detailed order analytics with support for high-volume stores"""
    
    name = "analytics_order_summary"
    description = "Get order analytics including count, revenue, and product performance for a date range"
    context = """
    Fetches comprehensive order analytics for iDrinkCoffee.com.
    
    Features:
    - Handles 100-200+ daily orders efficiently
    - Automatic pagination for large datasets
    - Returns order count, revenue, top products
    - Supports date range queries
    - Includes average order value (AOV)
    
    Date formats:
    - YYYY-MM-DD (e.g., "2025-01-20")
    - Use "today" or "yesterday" for convenience
    
    Example queries:
    - Today's sales: start_date="today", end_date="today"
    - Last 7 days: start_date="2025-01-14", end_date="2025-01-20"
    - Yesterday only: start_date="yesterday", end_date="yesterday"
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "start_date": {
                "type": "string",
                "description": "Start date (YYYY-MM-DD or 'today'/'yesterday')"
            },
            "end_date": {
                "type": "string",
                "description": "End date (YYYY-MM-DD or 'today'/'yesterday')"
            },
            "include_products": {
                "type": "boolean",
                "description": "Include top products breakdown (default: true)",
                "default": True
            },
            "product_limit": {
                "type": "integer",
                "description": "Number of top products to return (default: 10)",
                "default": 10
            }
        },
        "required": ["start_date", "end_date"]
    }
    
    async def execute(self, start_date: str, end_date: str, 
                     include_products: bool = True, product_limit: int = 10) -> Dict[str, Any]:
        """Execute order analytics query with pagination support"""
        try:
            client = ShopifyClient()
            
            # Parse dates
            start_date = self._parse_date(start_date)
            end_date = self._parse_date(end_date)
            
            # Build query filter
            date_filter = f"created_at:>={start_date} created_at:<={end_date} financial_status:paid"
            
            # Initialize analytics data
            analytics = {
                "period": {
                    "start": start_date,
                    "end": end_date
                },
                "summary": {
                    "order_count": 0,
                    "total_revenue": 0.0,
                    "average_order_value": 0.0,
                    "currency": "USD"
                }
            }
            
            # Fetch all orders with pagination
            all_orders = []
            has_next_page = True
            cursor = None
            
            while has_next_page:
                # Build paginated query
                orders_query = self._build_orders_query(date_filter, cursor, include_products)
                
                result = client.execute_graphql(orders_query)
                orders_data = result.get('data', {}).get('orders', {})
                
                # Add orders to collection
                edges = orders_data.get('edges', [])
                all_orders.extend(edges)
                
                # Check for next page
                page_info = orders_data.get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False)
                
                if has_next_page and edges:
                    cursor = edges[-1].get('cursor')
            
            # Process analytics
            total_revenue = 0.0
            product_sales = {} if include_products else None
            
            for edge in all_orders:
                order = edge.get('node', {})
                
                # Add to revenue
                total_amount = order.get('totalPriceSet', {}).get('shopMoney', {}).get('amount', '0')
                total_revenue += float(total_amount)
                
                # Process line items for product analytics
                if include_products:
                    line_items = order.get('lineItems', {}).get('edges', [])
                    for item_edge in line_items:
                        item = item_edge.get('node', {})
                        product_title = item.get('title', 'Unknown Product')
                        sku = item.get('sku', 'NO-SKU')
                        quantity = item.get('quantity', 0)
                        price = float(item.get('originalUnitPriceSet', {}).get('shopMoney', {}).get('amount', '0'))
                        
                        # Aggregate by product
                        key = f"{product_title} ({sku})"
                        if key not in product_sales:
                            product_sales[key] = {
                                "title": product_title,
                                "sku": sku,
                                "quantity_sold": 0,
                                "revenue": 0.0
                            }
                        
                        product_sales[key]['quantity_sold'] += quantity
                        product_sales[key]['revenue'] += (price * quantity)
            
            # Update analytics
            analytics['summary']['order_count'] = len(all_orders)
            analytics['summary']['total_revenue'] = round(total_revenue, 2)
            analytics['summary']['average_order_value'] = round(total_revenue / len(all_orders), 2) if all_orders else 0
            
            # Add top products if requested
            if include_products and product_sales:
                # Sort by revenue and get top N
                sorted_products = sorted(product_sales.values(), key=lambda x: x['revenue'], reverse=True)
                analytics['top_products'] = sorted_products[:product_limit]
            
            # Add query cost info
            analytics['api_cost'] = {
                "queries_made": len(all_orders) // 250 + 1,
                "total_orders_fetched": len(all_orders)
            }
            
            return {
                "success": True,
                "data": analytics
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_date(self, date_str: str) -> str:
        """Parse date string to YYYY-MM-DD format"""
        if date_str.lower() == 'today':
            return datetime.now().strftime('%Y-%m-%d')
        elif date_str.lower() == 'yesterday':
            return (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            # Validate date format
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
                return date_str
            except ValueError:
                raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or 'today'/'yesterday'")
    
    def _build_orders_query(self, date_filter: str, cursor: Optional[str], include_line_items: bool) -> str:
        """Build GraphQL query with optional cursor for pagination"""
        after_clause = f', after: "{cursor}"' if cursor else ''
        
        line_items_fragment = """
            lineItems(first: 250) {
                edges {
                    node {
                        title
                        sku
                        quantity
                        originalUnitPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                    }
                }
            }
        """ if include_line_items else ""
        
        return f"""
        {{
            orders(first: 250, query: "{date_filter}"{after_clause}) {{
                edges {{
                    cursor
                    node {{
                        id
                        name
                        createdAt
                        totalPriceSet {{
                            shopMoney {{
                                amount
                                currencyCode
                            }}
                        }}
                        {line_items_fragment}
                    }}
                }}
                pageInfo {{
                    hasNextPage
                    endCursor
                }}
            }}
        }}
        """
    
    async def test(self) -> Dict[str, Any]:
        """Test with yesterday's data"""
        try:
            result = await self.execute("yesterday", "yesterday", include_products=False)
            if result["success"]:
                order_count = result['data']['summary']['order_count']
                return {
                    "status": "passed",
                    "message": f"Found {order_count} orders yesterday"
                }
            else:
                return {
                    "status": "failed",
                    "error": result["error"]
                }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }