"""
Native MCP implementation for managing Miele MAP sales
"""

from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Tuple
from ..base import BaseMCPTool, ShopifyClient

class ManageMieleSalesTool(BaseMCPTool):
    """Manage Miele MAP sales based on 2025 calendar"""
    
    name = "manage_miele_sales"
    description = "Manage Miele MAP (Minimum Advertised Price) sales"
    context = """
    Manages MAP sales for Miele products at iDrinkCoffee.com based on approved windows.
    
    Features:
    - Check current/upcoming sales
    - Apply sale prices with tags
    - Revert prices after sales end
    - Preview changes before applying
    
    Products managed:
    - CM5310: Entry-level super-automatic
    - CM6160: Mid-range with milk system
    - CM6360: Premium (CleanSteel/LotusWhite)
    - CM7750: Top-tier built-in model
    
    Actions:
    - check: Check active sales for a date
    - apply: Apply sale prices and tags
    - revert: Revert to regular prices
    - preview: Show upcoming sales
    
    Business Rules:
    - Sales use MAP-approved prices only
    - Tags: miele-sale, sale-YYYY-MM
    - Compare-at price shows original
    - Sales typically run 7-14 days
    - Some products excluded from certain sales
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check", "apply", "revert", "preview"],
                "description": "Action to perform"
            },
            "date": {
                "type": "string",
                "description": "Date for operations (YYYY-MM-DD)"
            },
            "dry_run": {
                "type": "boolean",
                "description": "Preview without applying changes",
                "default": False
            },
            "force": {
                "type": "boolean",
                "description": "Force apply even if already on sale",
                "default": False
            }
        },
        "required": ["action"]
    }
    
    def __init__(self):
        super().__init__()
        
        # Product definitions
        self.products = {
            "CM5310": {
                "product_id": "gid://shopify/Product/6973208133666",
                "regular_price": "1849.99",
                "variants": [
                    {"id": "gid://shopify/ProductVariant/40299653726242", "sku": "MIL-CM5310"}
                ]
            },
            "CM6160": {
                "product_id": "gid://shopify/Product/6976161841186",
                "regular_price": "2599.99",
                "variants": [
                    {"id": "gid://shopify/ProductVariant/40309728018466", "sku": "MIL-CM6160"}
                ]
            },
            "CM6360_CleanSteel": {
                "product_id": "gid://shopify/Product/7022600486946",
                "regular_price": "2999.99",
                "variants": [
                    {"id": "gid://shopify/ProductVariant/40471828889634", "sku": "MIL-CM6360-S"}
                ]
            },
            "CM6360_LotusWhite": {
                "product_id": "gid://shopify/Product/7188667498530",
                "regular_price": "2999.99",
                "variants": [
                    {"id": "gid://shopify/ProductVariant/41052773253154", "sku": "MIL-CM6360-W"}
                ]
            },
            "CM7750": {
                "product_id": "gid://shopify/Product/6976240844834",
                "regular_price": "5999.99",
                "variants": [
                    {"id": "gid://shopify/ProductVariant/40309899755554", "sku": "MIL-CM7750"}
                ]
            }
        }
        
        # Sale windows for 2025
        self.sale_windows = [
            # New Year Sale
            ("2024-12-27", "2025-01-02", {
                "CM5310": "1449.99",
                "CM6160": "2049.99"
            }),
            # January sales
            ("2025-01-10", "2025-01-16", {
                "CM5310": "1499.99",
                "CM6360": "2499.99",  # Applies to both colors
                "CM7750": "5499.99"
            }),
            ("2025-01-17", "2025-01-23", {
                "CM6160": "2099.99"
            }),
            ("2025-01-30", "2025-02-06", {
                "CM5310": "1449.99",
                "CM6160": "2099.99",
                "CM7750": "5499.99"
            }),
            # Valentine's Day
            ("2025-02-07", "2025-02-13", {
                "CM5310": "1449.99",
                "CM6360": "2399.99"
            }),
            # Add more sale windows as needed...
        ]
    
    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """Execute Miele sales management action"""
        try:
            target_date = kwargs.get('date')
            if target_date:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            else:
                target_date = date.today()
            
            dry_run = kwargs.get('dry_run', False)
            force = kwargs.get('force', False)
            
            if action == "check":
                return await self._check_sales(target_date)
            elif action == "apply":
                return await self._apply_sales(target_date, dry_run, force)
            elif action == "revert":
                return await self._revert_sales(target_date, dry_run)
            elif action == "preview":
                return await self._preview_sales()
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
    
    async def _check_sales(self, check_date: date) -> Dict[str, Any]:
        """Check what sales should be active on a date"""
        active_sales = []
        
        for start_str, end_str, sale_prices in self.sale_windows:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            
            if start_date <= check_date <= end_date:
                # Process each product in the sale
                for product_key, sale_price in sale_prices.items():
                    # Handle CM6360 which has two color variants
                    if product_key == "CM6360":
                        for color in ["CleanSteel", "LotusWhite"]:
                            key = f"CM6360_{color}"
                            if key in self.products:
                                product = self.products[key]
                                active_sales.append({
                                    "product": key,
                                    "product_id": product["product_id"],
                                    "regular_price": float(product["regular_price"]),
                                    "sale_price": float(sale_price),
                                    "savings": float(product["regular_price"]) - float(sale_price),
                                    "discount_percent": round((float(product["regular_price"]) - float(sale_price)) / float(product["regular_price"]) * 100, 1),
                                    "start_date": start_str,
                                    "end_date": end_str
                                })
                    elif product_key in self.products:
                        product = self.products[product_key]
                        active_sales.append({
                            "product": product_key,
                            "product_id": product["product_id"],
                            "regular_price": float(product["regular_price"]),
                            "sale_price": float(sale_price),
                            "savings": float(product["regular_price"]) - float(sale_price),
                            "discount_percent": round((float(product["regular_price"]) - float(sale_price)) / float(product["regular_price"]) * 100, 1),
                            "start_date": start_str,
                            "end_date": end_str
                        })
        
        return {
            "success": True,
            "date": str(check_date),
            "active_sales": active_sales,
            "count": len(active_sales),
            "total_savings": sum(s["savings"] for s in active_sales)
        }
    
    async def _apply_sales(self, target_date: date, dry_run: bool, force: bool) -> Dict[str, Any]:
        """Apply sale prices and tags"""
        # Get active sales
        check_result = await self._check_sales(target_date)
        active_sales = check_result['active_sales']
        
        if not active_sales:
            return {
                "success": True,
                "message": f"No sales to apply for {target_date}",
                "date": str(target_date)
            }
        
        client = ShopifyClient()
        results = []
        sale_tag = f"sale-{target_date.strftime('%Y-%m')}"
        
        for sale in active_sales:
            product_key = sale['product']
            product_info = self.products[product_key]
            
            if dry_run:
                results.append({
                    "product": product_key,
                    "status": "dry_run",
                    "actions": [
                        f"Would set price to ${sale['sale_price']}",
                        f"Would set compare-at to ${sale['regular_price']}",
                        f"Would add tags: miele-sale, {sale_tag}"
                    ]
                })
                continue
            
            # Update variants
            variants_input = []
            for variant in product_info['variants']:
                variants_input.append({
                    "id": variant['id'],
                    "price": str(sale['sale_price']),
                    "compareAtPrice": str(sale['regular_price'])
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
                "productId": product_info['product_id'],
                "variants": variants_input
            }
            
            response = client.execute_graphql(mutation, variables)
            
            if response.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
                errors = response['data']['productVariantsBulkUpdate']['userErrors']
                results.append({
                    "product": product_key,
                    "status": "error",
                    "errors": errors
                })
                continue
            
            # Add tags
            tag_mutation = '''
            mutation addTags($id: ID!, $tags: [String!]!) {
                tagsAdd(id: $id, tags: $tags) {
                    node {
                        ... on Product {
                            id
                        }
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            tag_response = client.execute_graphql(tag_mutation, {
                "id": product_info['product_id'],
                "tags": ["miele-sale", sale_tag]
            })
            
            results.append({
                "product": product_key,
                "status": "success",
                "sale_price": sale['sale_price'],
                "savings": sale['savings'],
                "discount_percent": sale['discount_percent']
            })
        
        return {
            "success": True,
            "date": str(target_date),
            "dry_run": dry_run,
            "applied_sales": len([r for r in results if r.get('status') == 'success']),
            "errors": len([r for r in results if r.get('status') == 'error']),
            "results": results
        }
    
    async def _revert_sales(self, target_date: date, dry_run: bool) -> Dict[str, Any]:
        """Revert all Miele products to regular prices"""
        client = ShopifyClient()
        results = []
        sale_tag = f"sale-{target_date.strftime('%Y-%m')}"
        
        for product_key, product_info in self.products.items():
            if dry_run:
                results.append({
                    "product": product_key,
                    "status": "dry_run",
                    "actions": [
                        f"Would set price to ${product_info['regular_price']}",
                        "Would clear compare-at price",
                        f"Would remove tags: miele-sale, {sale_tag}"
                    ]
                })
                continue
            
            # Update variants
            variants_input = []
            for variant in product_info['variants']:
                variants_input.append({
                    "id": variant['id'],
                    "price": str(product_info['regular_price']),
                    "compareAtPrice": None
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
                "productId": product_info['product_id'],
                "variants": variants_input
            }
            
            response = client.execute_graphql(mutation, variables)
            
            if response.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
                errors = response['data']['productVariantsBulkUpdate']['userErrors']
                results.append({
                    "product": product_key,
                    "status": "error",
                    "errors": errors
                })
                continue
            
            # Remove tags
            tag_mutation = '''
            mutation removeTags($id: ID!, $tags: [String!]!) {
                tagsRemove(id: $id, tags: $tags) {
                    node {
                        ... on Product {
                            id
                        }
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            '''
            
            tag_response = client.execute_graphql(tag_mutation, {
                "id": product_info['product_id'],
                "tags": ["miele-sale", sale_tag]
            })
            
            results.append({
                "product": product_key,
                "status": "success",
                "regular_price": product_info['regular_price']
            })
        
        return {
            "success": True,
            "date": str(target_date),
            "dry_run": dry_run,
            "reverted": len([r for r in results if r.get('status') == 'success']),
            "errors": len([r for r in results if r.get('status') == 'error']),
            "results": results
        }
    
    async def _preview_sales(self) -> Dict[str, Any]:
        """Preview upcoming sales"""
        today = date.today()
        upcoming = []
        
        for start_str, end_str, sale_prices in self.sale_windows:
            start_date = datetime.strptime(start_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_str, '%Y-%m-%d').date()
            
            # Include past 30 days and future sales
            if end_date >= today - timedelta(days=30):
                status = "active" if start_date <= today <= end_date else ("upcoming" if start_date > today else "past")
                
                products_in_sale = []
                for product_key, sale_price in sale_prices.items():
                    if product_key == "CM6360":
                        # Handle both color variants
                        for color in ["CleanSteel", "LotusWhite"]:
                            key = f"CM6360_{color}"
                            if key in self.products:
                                product = self.products[key]
                                products_in_sale.append({
                                    "product": key,
                                    "regular_price": float(product["regular_price"]),
                                    "sale_price": float(sale_price),
                                    "discount_percent": round((float(product["regular_price"]) - float(sale_price)) / float(product["regular_price"]) * 100, 1)
                                })
                    elif product_key in self.products:
                        product = self.products[product_key]
                        products_in_sale.append({
                            "product": product_key,
                            "regular_price": float(product["regular_price"]),
                            "sale_price": float(sale_price),
                            "discount_percent": round((float(product["regular_price"]) - float(sale_price)) / float(product["regular_price"]) * 100, 1)
                        })
                
                upcoming.append({
                    "start_date": start_str,
                    "end_date": end_str,
                    "status": status,
                    "days_until": (start_date - today).days if start_date > today else 0,
                    "products": products_in_sale
                })
        
        return {
            "success": True,
            "current_date": str(today),
            "total_sales": len(upcoming),
            "active_sales": len([s for s in upcoming if s["status"] == "active"]),
            "upcoming_sales": len([s for s in upcoming if s["status"] == "upcoming"]),
            "sales": upcoming
        }
    
    async def test(self) -> Dict[str, Any]:
        """Test Miele sales management"""
        try:
            # Test date parsing
            test_date = date.today()
            result = await self._check_sales(test_date)
            
            return {
                "status": "passed",
                "message": "Miele sales tool ready",
                "products_configured": len(self.products),
                "sale_windows_configured": len(self.sale_windows)
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }