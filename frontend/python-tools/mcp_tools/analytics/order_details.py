"""
Order details tool - fetch specific order information for review and analysis
"""

from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timedelta
from ..base import BaseMCPTool, ShopifyClient

class OrderDetailsTool(BaseMCPTool):
    """Get detailed order information including customer data for business review"""
    
    name = "analytics_order_details"
    description = "Get detailed order information including customer names, emails, and order specifics for business analysis"
    context = """
    Fetches detailed order information for business analysis and review purposes.
    
    Features:
    - Individual order details with customer information
    - Risk assessment data (payment status, amounts)
    - Order IDs and Shopify admin links
    - Supports date ranges and filtering
    - Designed for legitimate business purposes like fraud review
    
    Use cases:
    - ClearSale fraud review coordination
    - High-value order verification  
    - Payment dispute analysis
    - Customer service investigations
    - Risk assessment reviews
    
    Date formats:
    - YYYY-MM-DD (e.g., "2025-01-20")
    - Use "today" or "yesterday" for convenience
    - Date ranges: start_date to end_date
    
    IMPORTANT: This tool provides customer data for legitimate business purposes only.
    Use responsibly and in compliance with privacy policies.
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
                "description": "End date (YYYY-MM-DD or 'today'/'yesterday')",
                "default": "today"
            },
            "min_amount": {
                "type": "number",
                "description": "Minimum order amount (for high-value order filtering)",
                "default": 0
            },
            "max_amount": {
                "type": "number",
                "description": "Maximum order amount (optional)"
            },
            "payment_status": {
                "type": "string",
                "description": "Filter by payment status",
                "enum": ["paid", "pending", "refunded", "voided", "all"],
                "default": "paid"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of orders to return (default: 50)",
                "default": 50
            },
            "risk_level": {
                "type": "string",
                "description": "Filter by risk level (if available)",
                "enum": ["low", "medium", "high", "all"],
                "default": "all"
            }
        },
        "required": ["start_date"]
    }
    
    async def execute(self, start_date: str, end_date: str = "today", 
                     min_amount: float = 0, max_amount: Optional[float] = None,
                     payment_status: str = "paid", limit: int = 50,
                     risk_level: str = "all") -> Dict[str, Any]:
        """Get detailed order information"""
        try:
            client = ShopifyClient()
            
            # Parse dates
            start_date = self._parse_date(start_date)
            end_date = self._parse_date(end_date)
            
            # Build query filter
            if payment_status == "all":
                date_filter = f"created_at:>={start_date} created_at:<={end_date}"
            else:
                date_filter = f"created_at:>={start_date} created_at:<={end_date} financial_status:{payment_status}"
            
            # Initialize results
            results = {
                "period": {
                    "start": start_date,
                    "end": end_date
                },
                "filters": {
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "payment_status": payment_status,
                    "risk_level": risk_level,
                    "limit": limit
                },
                "orders": []
            }
            
            # Fetch orders with pagination
            all_orders = []
            has_next_page = True
            cursor = None
            fetched_count = 0
            
            while has_next_page and fetched_count < limit:
                # Calculate remaining to fetch
                remaining = limit - fetched_count
                fetch_size = min(250, remaining)
                
                # Build paginated query
                orders_query = self._build_detailed_orders_query(date_filter, cursor, fetch_size)
                
                result = client.execute_graphql(orders_query)
                orders_data = result.get('data', {}).get('orders', {})
                
                # Add orders to collection
                edges = orders_data.get('edges', [])
                for edge in edges:
                    order = self._process_order_details(edge.get('node', {}))
                    
                    # Apply amount filtering
                    order_amount = float(order.get('total_amount', 0))
                    if order_amount < min_amount:
                        continue
                    if max_amount is not None and order_amount > max_amount:
                        continue
                    
                    all_orders.append(order)
                    fetched_count += 1
                    
                    if fetched_count >= limit:
                        break
                
                # Check for next page
                page_info = orders_data.get('pageInfo', {})
                has_next_page = page_info.get('hasNextPage', False) and fetched_count < limit
                
                if has_next_page and edges:
                    cursor = edges[-1].get('cursor')
            
            results["orders"] = all_orders
            results["total_found"] = len(all_orders)
            
            # Add summary statistics
            if all_orders:
                total_value = sum(float(order.get('total_amount', 0)) for order in all_orders)
                results["summary"] = {
                    "order_count": len(all_orders),
                    "total_value": round(total_value, 2),
                    "average_order_value": round(total_value / len(all_orders), 2),
                    "date_range": f"{start_date} to {end_date}"
                }
            
            return {
                "success": True,
                "data": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _build_detailed_orders_query(self, date_filter: str, cursor: Optional[str], limit: int) -> str:
        """Build GraphQL query for detailed order information"""
        after_clause = f', after: "{cursor}"' if cursor else ''
        
        return f"""
        {{
            orders(first: {limit}, query: "{date_filter}"{after_clause}) {{
                edges {{
                    cursor
                    node {{
                        id
                        name
                        createdAt
                        processedAt
                        totalPriceSet {{
                            shopMoney {{
                                amount
                                currencyCode
                            }}
                        }}
                        subtotalPriceSet {{
                            shopMoney {{
                                amount
                            }}
                        }}
                        totalTaxSet {{
                            shopMoney {{
                                amount
                            }}
                        }}
                        displayFinancialStatus
                        displayFulfillmentStatus
                        customer {{
                            id
                            firstName
                            lastName
                            email
                            phone
                        }}
                        billingAddress {{
                            firstName
                            lastName
                            address1
                            city
                            province
                            country
                            zip
                        }}
                        shippingAddress {{
                            firstName
                            lastName
                            address1
                            city
                            province
                            country
                            zip
                        }}
                        riskLevel
                        paymentGatewayNames
                        sourceIdentifier
                        tags
                        note
                        lineItems(first: 10) {{
                            edges {{
                                node {{
                                    title
                                    quantity
                                    originalUnitPriceSet {{
                                        shopMoney {{
                                            amount
                                        }}
                                    }}
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
        """
    
    def _process_order_details(self, order_node: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format order details"""
        # Extract basic order info
        order_id = order_node.get('id', '').split('/')[-1] if order_node.get('id') else 'Unknown'
        order_name = order_node.get('name', 'Unknown')
        
        # Extract customer info
        customer = order_node.get('customer', {})
        customer_info = {
            "name": f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip() or "Guest",
            "email": customer.get('email', 'No email'),
            "phone": customer.get('phone', 'No phone')
        }
        
        # Extract amounts
        total_price = order_node.get('totalPriceSet', {}).get('shopMoney', {})
        subtotal_price = order_node.get('subtotalPriceSet', {}).get('shopMoney', {})
        tax_amount = order_node.get('totalTaxSet', {}).get('shopMoney', {})
        
        # Extract addresses
        billing = order_node.get('billingAddress', {})
        shipping = order_node.get('shippingAddress', {})
        
        # Extract line items
        line_items = []
        for item_edge in order_node.get('lineItems', {}).get('edges', []):
            item = item_edge.get('node', {})
            line_items.append({
                "title": item.get('title', 'Unknown Product'),
                "quantity": item.get('quantity', 0),
                "unit_price": float(item.get('originalUnitPriceSet', {}).get('shopMoney', {}).get('amount', 0))
            })
        
        return {
            "order_id": order_id,
            "order_name": order_name,
            "admin_link": f"https://idrinkcoffee.myshopify.com/admin/orders/{order_id}",
            "created_at": order_node.get('createdAt', 'Unknown'),
            "processed_at": order_node.get('processedAt', 'Not processed'),
            "total_amount": float(total_price.get('amount', 0)),
            "subtotal": float(subtotal_price.get('amount', 0)),
            "tax_amount": float(tax_amount.get('amount', 0)),
            "currency": total_price.get('currencyCode', 'USD'),
            "financial_status": order_node.get('displayFinancialStatus', 'Unknown'),
            "fulfillment_status": order_node.get('displayFulfillmentStatus', 'Unknown'),
            "risk_level": order_node.get('riskLevel', 'Unknown'),
            "payment_gateway": ', '.join(order_node.get('paymentGatewayNames', [])),
            "source": order_node.get('sourceIdentifier', 'Unknown'),
            "customer": customer_info,
            "billing_address": {
                "name": f"{billing.get('firstName', '')} {billing.get('lastName', '')}".strip(),
                "address": billing.get('address1', 'No address'),
                "city": billing.get('city', 'No city'),
                "province": billing.get('province', 'No province'),
                "country": billing.get('country', 'No country'),
                "zip": billing.get('zip', 'No zip')
            },
            "shipping_address": {
                "name": f"{shipping.get('firstName', '')} {shipping.get('lastName', '')}".strip(),
                "address": shipping.get('address1', 'No address'),
                "city": shipping.get('city', 'No city'),
                "province": shipping.get('province', 'No province'),
                "country": shipping.get('country', 'No country'),
                "zip": shipping.get('zip', 'No zip')
            },
            "tags": order_node.get('tags', []),
            "note": order_node.get('note', ''),
            "line_items": line_items,
            "line_item_count": len(line_items)
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
    
    async def test(self) -> Dict[str, Any]:
        """Test with recent orders"""
        try:
            # Get orders from last 3 days with limit of 5 
            start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            result = await self.execute(start_date, "today", limit=5)
            
            if result["success"]:
                order_count = result['data']['total_found']
                return {
                    "status": "passed",
                    "message": f"Found {order_count} detailed orders in last 3 days"
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