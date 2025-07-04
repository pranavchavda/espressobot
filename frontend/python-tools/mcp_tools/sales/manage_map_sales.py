"""
Native MCP implementation for managing MAP (Minimum Advertised Price) sales
"""

import re
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from ..base import BaseMCPTool, ShopifyClient

class ManageMAPSalesTool(BaseMCPTool):
    """Manage MAP sales based on calendar data"""
    
    name = "manage_map_sales"
    description = "Manage MAP (Minimum Advertised Price) sales based on calendar data"
    context = """
    Manages MAP sales for Breville products at iDrinkCoffee.com using a markdown calendar.
    
    Features:
    - Check active sales for any date
    - Apply sale prices for date ranges
    - Revert prices back to regular
    - Show calendar summary
    
    The calendar format (markdown):
    ## 30 May - 05 Jun
    | Product | Color | SKU | Regular | Sale | Discount | Product ID | Variant ID |
    |---------|-------|-----|---------|------|----------|------------|------------|
    | Barista Express | Black | BES870XL | $699.95 | $599.95 | 14% off | gid://... | gid://... |
    
    Actions:
    - check: Check what sales should be active
    - apply: Apply sale prices for a date
    - revert: Revert prices to regular
    - summary: Show all scheduled sales
    
    Business Rules:
    - Sales run from Thursday to Wednesday
    - Prices include compare-at for strike-through
    - Handles year boundaries (Dec-Jan sales)
    - Groups variants by product for bulk updates
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check", "apply", "revert", "summary"],
                "description": "Action to perform"
            },
            "calendar_file": {
                "type": "string",
                "description": "Path to calendar markdown file",
                "default": "resources/breville_espresso_sales_2025_enhanced.md"
            },
            "date": {
                "type": "string",
                "description": "Date for check/apply actions (YYYY-MM-DD)"
            },
            "date_range": {
                "type": "string",
                "description": "Date range for revert (e.g., '30 May - 05 Jun')"
            },
            "dry_run": {
                "type": "boolean",
                "description": "Preview changes without applying",
                "default": False
            }
        },
        "required": ["action"]
    }
    
    def __init__(self):
        super().__init__()
        self.sales_data = {}
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute MAP sales management action"""
        try:
            calendar_file = kwargs.get('calendar_file', 'resources/breville_espresso_sales_2025_enhanced.md')
            dry_run = kwargs.get('dry_run', False)
            
            # Load calendar
            calendar_path = Path(calendar_file)
            if not calendar_path.exists():
                # Try relative to python-tools directory
                calendar_path = Path(__file__).parent.parent.parent.parent / calendar_file
                if not calendar_path.exists():
                    return {
                        "success": False,
                        "error": f"Calendar file not found: {calendar_file}"
                    }
            
            await self._load_calendar(calendar_path)
            
            if action == "check":
                return await self._check_sales(kwargs.get('date'))
            elif action == "apply":
                return await self._apply_sales(kwargs.get('date'), dry_run)
            elif action == "revert":
                date_range = kwargs.get('date_range')
                if not date_range:
                    return {
                        "success": False,
                        "error": "date_range required for revert action"
                    }
                return await self._revert_prices(date_range, dry_run)
            elif action == "summary":
                return await self._show_summary()
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action
            }
    
    async def _load_calendar(self, calendar_path: Path):
        """Load and parse the markdown calendar"""
        with open(calendar_path, 'r') as f:
            content = f.read()
        
        # Parse markdown sections by date ranges
        date_pattern = r'^## (.+ - .+)$'
        current_date_range = None
        
        for line in content.split('\n'):
            # Check for date range header
            date_match = re.match(date_pattern, line)
            if date_match:
                current_date_range = date_match.group(1)
                self.sales_data[current_date_range] = []
                continue
            
            # Parse table rows
            if current_date_range and line.startswith('|') and not line.startswith('| Product') and not line.startswith('|---'):
                parts = [p.strip() for p in line.split('|')[1:-1]]
                if len(parts) >= 8:
                    product_data = {
                        'product_title': parts[0],
                        'color': parts[1],
                        'sku': parts[2],
                        'regular_price': float(parts[3].replace('$', '').replace(',', '')),
                        'sale_price': float(parts[4].replace('$', '').replace(',', '')),
                        'discount': parts[5],
                        'product_id': parts[6],
                        'variant_id': parts[7] if len(parts) > 7 else None
                    }
                    self.sales_data[current_date_range].append(product_data)
    
    def _parse_date_range(self, date_range: str) -> Tuple[date, date]:
        """Parse date range string into start and end dates"""
        parts = date_range.split(' - ')
        
        # Parse start date
        start_parts = parts[0].split(' ')
        start_day = int(start_parts[0])
        start_month = start_parts[1]
        
        # Parse end date
        end_parts = parts[1].split(' ')
        end_day = int(end_parts[0])
        end_month = end_parts[1]
        
        # Convert month names to numbers
        months = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }
        
        start_month_num = months[start_month]
        end_month_num = months[end_month]
        
        # Determine year
        current_year = datetime.now().year
        start_year = current_year
        end_year = current_year
        
        # Handle year boundary
        if start_month_num == 12 and end_month_num == 1:
            end_year = current_year + 1
        
        start_date = date(start_year, start_month_num, start_day)
        end_date = date(end_year, end_month_num, end_day)
        
        return start_date, end_date
    
    async def _check_sales(self, check_date: Optional[str]) -> Dict[str, Any]:
        """Check what sales should be active on a date"""
        if check_date:
            target_date = datetime.strptime(check_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()
        
        active_sales = []
        
        for date_range, products in self.sales_data.items():
            start_date, end_date = self._parse_date_range(date_range)
            
            if start_date <= target_date <= end_date:
                active_sales.extend(products)
        
        return {
            "success": True,
            "date": str(target_date),
            "active_sales": active_sales,
            "count": len(active_sales),
            "total_discount": sum(p['regular_price'] - p['sale_price'] for p in active_sales)
        }
    
    async def _apply_sales(self, apply_date: Optional[str], dry_run: bool) -> Dict[str, Any]:
        """Apply sale prices for all products on a date"""
        if apply_date:
            target_date = datetime.strptime(apply_date, '%Y-%m-%d').date()
        else:
            target_date = date.today()
        
        # Get active sales
        check_result = await self._check_sales(str(target_date))
        active_sales = check_result['active_sales']
        
        if not active_sales:
            return {
                "success": True,
                "message": f"No sales to apply for {target_date}",
                "date": str(target_date)
            }
        
        client = ShopifyClient()
        
        # Group by product ID for bulk updates
        product_groups = {}
        skipped = []
        
        for product in active_sales:
            if product['product_id'] == 'NOT_FOUND':
                skipped.append(product)
                continue
            
            # Get variant ID if needed
            if not product.get('variant_id'):
                variant_id = await self._get_variant_id(client, product['product_id'])
                if not variant_id:
                    skipped.append(product)
                    continue
                product['variant_id'] = variant_id
            
            if product['product_id'] not in product_groups:
                product_groups[product['product_id']] = []
            product_groups[product['product_id']].append(product)
        
        # Apply updates
        results = []
        
        for product_id, variants in product_groups.items():
            if dry_run:
                results.append({
                    "product_id": product_id,
                    "variants_count": len(variants),
                    "status": "dry_run",
                    "variants": [
                        {
                            "title": v['product_title'],
                            "color": v['color'],
                            "sku": v['sku'],
                            "regular_price": v['regular_price'],
                            "sale_price": v['sale_price'],
                            "discount": v['discount']
                        } for v in variants
                    ]
                })
                continue
            
            # Build variants input
            variants_input = []
            for variant in variants:
                variants_input.append({
                    "id": variant['variant_id'],
                    "price": str(variant['sale_price']),
                    "compareAtPrice": str(variant['regular_price'])
                })
            
            # Update using bulk mutation
            mutation = '''
            mutation updateVariantPrices($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants {
                        id
                        price
                        compareAtPrice
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            variables = {
                "productId": product_id,
                "variants": variants_input
            }
            
            response = client.execute_graphql(mutation, variables)
            
            if response.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
                errors = response['data']['productVariantsBulkUpdate']['userErrors']
                results.append({
                    "product_id": product_id,
                    "status": "error",
                    "errors": errors
                })
            else:
                results.append({
                    "product_id": product_id,
                    "variants_count": len(variants),
                    "status": "success"
                })
        
        success_count = sum(1 for r in results if r.get('status') == 'success')
        error_count = sum(1 for r in results if r.get('status') == 'error')
        
        return {
            "success": True,
            "date": str(target_date),
            "dry_run": dry_run,
            "summary": {
                "total_products": len(active_sales),
                "updated": success_count,
                "errors": error_count,
                "skipped": len(skipped)
            },
            "results": results,
            "skipped": skipped
        }
    
    async def _revert_prices(self, date_range: str, dry_run: bool) -> Dict[str, Any]:
        """Revert prices back to regular for a date range"""
        if date_range not in self.sales_data:
            return {
                "success": False,
                "error": f"Date range '{date_range}' not found in calendar"
            }
        
        products = self.sales_data[date_range]
        client = ShopifyClient()
        
        # Group by product ID
        product_groups = {}
        skipped = []
        
        for product in products:
            if product['product_id'] == 'NOT_FOUND':
                skipped.append(product)
                continue
            
            # Get variant ID if needed
            if not product.get('variant_id'):
                variant_id = await self._get_variant_id(client, product['product_id'])
                if not variant_id:
                    skipped.append(product)
                    continue
                product['variant_id'] = variant_id
            
            if product['product_id'] not in product_groups:
                product_groups[product['product_id']] = []
            product_groups[product['product_id']].append(product)
        
        # Apply reverts
        results = []
        
        for product_id, variants in product_groups.items():
            if dry_run:
                results.append({
                    "product_id": product_id,
                    "variants_count": len(variants),
                    "status": "dry_run",
                    "action": "would_revert"
                })
                continue
            
            # Build variants input
            variants_input = []
            for variant in variants:
                variants_input.append({
                    "id": variant['variant_id'],
                    "price": str(variant['regular_price']),
                    "compareAtPrice": None  # Clear compare-at
                })
            
            # Update using bulk mutation
            mutation = '''
            mutation updateVariantPrices($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                    productVariants {
                        id
                        price
                        compareAtPrice
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            variables = {
                "productId": product_id,
                "variants": variants_input
            }
            
            response = client.execute_graphql(mutation, variables)
            
            if response.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
                errors = response['data']['productVariantsBulkUpdate']['userErrors']
                results.append({
                    "product_id": product_id,
                    "status": "error",
                    "errors": errors
                })
            else:
                results.append({
                    "product_id": product_id,
                    "variants_count": len(variants),
                    "status": "success"
                })
        
        success_count = sum(1 for r in results if r.get('status') == 'success')
        error_count = sum(1 for r in results if r.get('status') == 'error')
        
        return {
            "success": True,
            "date_range": date_range,
            "dry_run": dry_run,
            "summary": {
                "total_products": len(products),
                "reverted": success_count,
                "errors": error_count,
                "skipped": len(skipped)
            },
            "results": results
        }
    
    async def _show_summary(self) -> Dict[str, Any]:
        """Show calendar summary"""
        summary = []
        today = date.today()
        
        for date_range in sorted(self.sales_data.keys(), 
                                key=lambda x: self._parse_date_range(x)[0]):
            products = self.sales_data[date_range]
            start_date, end_date = self._parse_date_range(date_range)
            
            # Check if active
            is_active = start_date <= today <= end_date
            
            # Group by product name
            product_groups = {}
            for p in products:
                name = p['product_title'].split(' - ')[0]
                if name not in product_groups:
                    product_groups[name] = []
                product_groups[name].append(p)
            
            summary.append({
                "date_range": date_range,
                "start_date": str(start_date),
                "end_date": str(end_date),
                "is_active": is_active,
                "total_products": len(products),
                "product_groups": [
                    {
                        "name": name,
                        "variants": len(variants),
                        "discount": variants[0]['discount']
                    } for name, variants in product_groups.items()
                ]
            })
        
        return {
            "success": True,
            "total_sale_periods": len(summary),
            "active_periods": sum(1 for s in summary if s['is_active']),
            "sales": summary
        }
    
    async def _get_variant_id(self, client: ShopifyClient, product_id: str) -> Optional[str]:
        """Get first variant ID for a product"""
        query = '''
        query getProductVariant($id: ID!) {
            product(id: $id) {
                variants(first: 1) {
                    edges {
                        node {
                            id
                        }
                    }
                }
            }
        }
        '''
        
        try:
            response = client.execute_graphql(query, {"id": product_id})
            if response and 'data' in response and response['data'].get('product'):
                variants = response['data']['product'].get('variants', {}).get('edges', [])
                if variants:
                    return variants[0]['node']['id']
        except Exception:
            pass
        
        return None
    
    async def test(self) -> Dict[str, Any]:
        """Test MAP sales management"""
        # Just verify we can parse a date range
        try:
            test_range = "30 May - 05 Jun"
            start, end = self._parse_date_range(test_range)
            return {
                "status": "passed",
                "message": "Date parsing works correctly"
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }