"""
Daily sales summary tool - optimized for quick daily metrics
"""

from typing import Dict, Any, Optional
import json
from datetime import datetime, timedelta
from ..base import BaseMCPTool, ShopifyClient

class DailySalesTool(BaseMCPTool):
    """Get quick daily sales summary with minimal API calls"""
    
    name = "analytics_daily_sales"
    description = "Get today's or recent daily sales summary quickly"
    context = """
    Provides quick daily sales metrics optimized for performance.
    
    Features:
    - Fast summary without product details
    - Today's sales with hourly breakdown
    - Comparison with previous day
    - Order velocity tracking
    
    Perfect for:
    - Morning sales check
    - Real-time monitoring
    - Quick performance updates
    
    Use order_analytics for detailed product breakdowns.
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Date to analyze (YYYY-MM-DD or 'today'/'yesterday')",
                "default": "today"
            },
            "include_hourly": {
                "type": "boolean",
                "description": "Include hourly breakdown (default: true for today)",
                "default": True
            },
            "compare_previous": {
                "type": "boolean",
                "description": "Include comparison with previous day",
                "default": True
            }
        }
    }
    
    async def execute(self, date: str = "today", include_hourly: bool = True, 
                     compare_previous: bool = True) -> Dict[str, Any]:
        """Get daily sales summary"""
        try:
            client = ShopifyClient()
            
            # Parse date
            target_date = self._parse_date(date)
            is_today = target_date == datetime.now().strftime('%Y-%m-%d')
            
            # Only include hourly for today
            if not is_today:
                include_hourly = False
            
            # Build main query
            results = {
                "date": target_date,
                "is_today": is_today,
                "summary": await self._get_day_summary(client, target_date)
            }
            
            # Add hourly breakdown if requested
            if include_hourly:
                results["hourly"] = await self._get_hourly_breakdown(client, target_date)
            
            # Add comparison if requested
            if compare_previous:
                previous_date = (datetime.strptime(target_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
                previous_summary = await self._get_day_summary(client, previous_date)
                
                results["comparison"] = {
                    "previous_date": previous_date,
                    "previous_orders": previous_summary["order_count"],
                    "previous_revenue": previous_summary["total_revenue"],
                    "order_change": results["summary"]["order_count"] - previous_summary["order_count"],
                    "revenue_change": round(results["summary"]["total_revenue"] - previous_summary["total_revenue"], 2),
                    "order_change_pct": self._calculate_percentage_change(
                        previous_summary["order_count"], 
                        results["summary"]["order_count"]
                    ),
                    "revenue_change_pct": self._calculate_percentage_change(
                        previous_summary["total_revenue"], 
                        results["summary"]["total_revenue"]
                    )
                }
            
            # Add current time for "today" queries
            if is_today:
                results["as_of"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                results["business_hours_remaining"] = self._calculate_remaining_hours()
            
            return {
                "success": True,
                "data": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_day_summary(self, client: ShopifyClient, date: str) -> Dict[str, Any]:
        """Get summary for a specific day"""
        date_filter = f"created_at:{date} financial_status:paid"
        
        query = f"""
        {{
            orders(first: 250, query: "{date_filter}") {{
                edges {{
                    node {{
                        totalPriceSet {{
                            shopMoney {{
                                amount
                            }}
                        }}
                    }}
                    cursor
                }}
                pageInfo {{
                    hasNextPage
                }}
            }}
        }}
        """
        
        # Execute query
        result = client.execute_graphql(query)
        data = result.get('data', {}).get('orders', {})
        
        edges = data.get('edges', [])
        order_count = 0
        
        # Calculate revenue from first page
        total_revenue = sum(
            float(edge.get('node', {}).get('totalPriceSet', {}).get('shopMoney', {}).get('amount', 0))
            for edge in edges
        )
        order_count += len(edges)
        
        # If there are more pages, fetch them
        if data.get('pageInfo', {}).get('hasNextPage', False) and edges:
            cursor = edges[-1].get('cursor')
            additional_data = await self._fetch_remaining_revenue(client, date_filter, cursor)
            total_revenue += additional_data['revenue']
            order_count += additional_data['count']
        
        return {
            "order_count": order_count,
            "total_revenue": round(total_revenue, 2),
            "average_order_value": round(total_revenue / order_count, 2) if order_count > 0 else 0
        }
    
    async def _fetch_remaining_revenue(self, client: ShopifyClient, date_filter: str, cursor: str) -> Dict[str, Any]:
        """Fetch remaining revenue with pagination"""
        total = 0.0
        count = 0
        has_next = True
        
        while has_next:
            query = f"""
            {{
                orders(first: 250, after: "{cursor}", query: "{date_filter}") {{
                    edges {{
                        node {{
                            totalPriceSet {{
                                shopMoney {{
                                    amount
                                }}
                            }}
                        }}
                        cursor
                    }}
                    pageInfo {{
                        hasNextPage
                    }}
                }}
            }}
            """
            
            result = client.execute_graphql(query)
            data = result.get('data', {}).get('orders', {})
            edges = data.get('edges', [])
            
            # Add revenue and count
            total += sum(
                float(edge.get('node', {}).get('totalPriceSet', {}).get('shopMoney', {}).get('amount', 0))
                for edge in edges
            )
            count += len(edges)
            
            # Check for next page
            has_next = data.get('pageInfo', {}).get('hasNextPage', False)
            if has_next and edges:
                cursor = edges[-1].get('cursor')
        
        return {"revenue": total, "count": count}
    
    async def _get_hourly_breakdown(self, client: ShopifyClient, date: str) -> Dict[str, Any]:
        """Get hourly breakdown for today"""
        hourly_data = {}
        
        # Generate hourly queries for business hours (6 AM to 10 PM)
        for hour in range(6, 23):  # 6 AM to 10 PM
            hour_start = f"{date}T{hour:02d}:00:00"
            hour_end = f"{date}T{hour+1:02d}:00:00"
            
            # Skip future hours
            if datetime.strptime(hour_start, '%Y-%m-%dT%H:%M:%S') > datetime.now():
                break
            
            query = f"""
            {{
                orders(first: 250, query: "created_at:>={hour_start} created_at:<{hour_end} financial_status:paid") {{
                    edges {{
                        node {{
                            id
                        }}
                    }}
                }}
            }}
            """
            
            result = client.execute_graphql(query)
            edges = result.get('data', {}).get('orders', {}).get('edges', [])
            count = len(edges)
            
            hourly_data[f"{hour:02d}:00"] = count
        
        return hourly_data
    
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
    
    def _calculate_percentage_change(self, old_value: float, new_value: float) -> float:
        """Calculate percentage change"""
        if old_value == 0:
            return 0.0 if new_value == 0 else 100.0
        return round(((new_value - old_value) / old_value) * 100, 2)
    
    def _calculate_remaining_hours(self) -> int:
        """Calculate remaining business hours (until 10 PM)"""
        now = datetime.now()
        closing_time = now.replace(hour=22, minute=0, second=0)  # 10 PM
        
        if now >= closing_time:
            return 0
        
        remaining = closing_time - now
        return int(remaining.total_seconds() / 3600)
    
    async def test(self) -> Dict[str, Any]:
        """Test with today's data"""
        try:
            result = await self.execute("today", include_hourly=False, compare_previous=False)
            if result["success"]:
                order_count = result['data']['summary']['order_count']
                return {
                    "status": "passed",
                    "message": f"Found {order_count} orders today so far"
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