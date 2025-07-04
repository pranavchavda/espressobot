"""
Native MCP implementation for create_full_product
"""

import os
import sys
import json
from typing import Dict, Any, List, Optional, Union

# Add parent directory to path so we can import the original tools
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from base import ShopifyClient
from ..base import BaseMCPTool

class CreateFullProductTool(BaseMCPTool):
    """Create a complete product with all metafields, tags, and proper configuration"""
    
    name = "create_full_product"
    description = "Create a fully-configured product with metafields, tags, and proper inventory settings"
    context = """
    This tool creates a complete product following iDrinkCoffee.com conventions:
    
    **Product Creation:**
    - Creates product with basic info (title, vendor, type, description)
    - Sets up pricing, SKU, and cost information
    - Configures inventory tracking and policies
    - Publishes to all relevant channels
    
    **Automatic Features:**
    - Auto-generates tags based on product type and vendor
    - Sets up proper inventory tracking (DENY policy)
    - Configures weight and dimensions
    - Publishes to all sales channels
    
    **Metafields Supported:**
    - Buy box content (marketing copy)
    - FAQs (structured Q&A)
    - Technical specifications
    - Variant preview names
    - Sale end dates
    - Coffee seasonality flags
    
    **Product Types:**
    - Espresso Machines (gets VIM/consumer tags)
    - Grinders (gets burr-grinder tags)
    - Fresh Coffee (gets seasonality support)
    - Accessories (gets warranty tags)
    - Parts & Cleaning supplies
    
    **Tag Categories:**
    - Product type tags
    - Vendor-specific tags (VIM for machines)
    - Custom tags from input
    - Warranty and consumer tags
    
    **Important Notes:**
    - Products are created in DRAFT status by default
    - Inventory policy is set to DENY (no overselling)
    - All products are published to sales channels
    - Metafields use proper namespaces and types
    """
    
    input_schema = {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Product title"
            },
            "vendor": {
                "type": "string",
                "description": "Product vendor/brand"
            },
            "product_type": {
                "type": "string",
                "description": "Product type (Espresso Machines, Grinders, Fresh Coffee, etc.)"
            },
            "description": {
                "type": "string",
                "description": "Product description (HTML supported)"
            },
            "handle": {
                "type": "string",
                "description": "URL handle (auto-generated if not provided)"
            },
            "price": {
                "type": "string",
                "description": "Product price (e.g., '699.99')"
            },
            "sku": {
                "type": "string",
                "description": "Product SKU"
            },
            "cost": {
                "type": "string",
                "description": "Cost of goods (COGS)"
            },
            "weight": {
                "type": "number",
                "description": "Product weight in grams"
            },
            "compare_at_price": {
                "type": "string",
                "description": "Compare at price"
            },
            "buybox": {
                "type": "string",
                "description": "Buy box marketing content"
            },
            "faqs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "question": {"type": "string"},
                        "answer": {"type": "string"}
                    }
                },
                "description": "FAQ entries"
            },
            "tech_specs": {
                "type": "object",
                "description": "Technical specifications as key-value pairs"
            },
            "variant_preview": {
                "type": "string",
                "description": "Variant preview name (e.g., 'Black')"
            },
            "sale_end": {
                "type": "string",
                "description": "Sale end date (ISO format)"
            },
            "seasonal": {
                "type": "boolean",
                "description": "Mark as seasonal coffee (for Fresh Coffee type)"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Additional custom tags"
            },
            "status": {
                "type": "string",
                "enum": ["DRAFT", "ACTIVE"],
                "description": "Product status (default: DRAFT)"
            },
            "auto_tags": {
                "type": "boolean",
                "description": "Generate automatic tags based on type/vendor (default: true)"
            }
        },
        "required": ["title", "vendor", "product_type", "price"]
    }
    
    async def execute(self, title: str, vendor: str, product_type: str, price: str,
                     description: Optional[str] = None, handle: Optional[str] = None,
                     sku: Optional[str] = None, cost: Optional[str] = None,
                     weight: Optional[float] = None, compare_at_price: Optional[str] = None,
                     buybox: Optional[str] = None, faqs: Optional[List[Dict[str, str]]] = None,
                     tech_specs: Optional[Dict[str, Any]] = None, variant_preview: Optional[str] = None,
                     sale_end: Optional[str] = None, seasonal: Optional[bool] = None,
                     tags: Optional[List[str]] = None, status: str = "DRAFT",
                     auto_tags: bool = True) -> Dict[str, Any]:
        """Execute product creation"""
        try:
            client = ShopifyClient()
            
            # Step 1: Create basic product
            product_data = {
                "title": title,
                "vendor": vendor,
                "productType": product_type,
                "status": status
            }
            
            if description:
                product_data["descriptionHtml"] = description
            
            if handle:
                product_data["handle"] = handle
            
            print(f"Creating product: {title}...")
            product_result = await self._create_product(client, product_data)
            
            if not product_result["success"]:
                return product_result
            
            product_id = product_result["product_id"]
            variant_id = product_result["variant_id"]
            inventory_item_id = product_result["inventory_item_id"]
            
            # Step 2: Update variant details
            if any([sku, cost, weight, price, compare_at_price]):
                print("Updating variant details...")
                variant_result = await self._update_variant_details(
                    client, product_id, variant_id, inventory_item_id,
                    sku=sku, cost=cost, weight=weight, price=price,
                    compare_at_price=compare_at_price
                )
                
                if not variant_result["success"]:
                    print(f"Warning: Failed to update variant details: {variant_result['error']}")
            
            # Step 3: Add metafields
            metafields = self._build_metafields(
                buybox=buybox, faqs=faqs, tech_specs=tech_specs,
                variant_preview=variant_preview, sale_end=sale_end,
                seasonal=seasonal, product_type=product_type
            )
            
            if metafields:
                print(f"Adding {len(metafields)} metafields...")
                metafield_result = await self._add_metafields(client, product_id, metafields)
                if not metafield_result["success"]:
                    print(f"Warning: Failed to add metafields: {metafield_result['error']}")
            
            # Step 4: Add tags
            if auto_tags or tags:
                all_tags = []
                
                if auto_tags:
                    all_tags.extend(self._get_product_type_tags(product_type))
                    all_tags.extend(self._get_vendor_tags(vendor, product_type))
                
                if tags:
                    all_tags.extend(tags)
                
                # Remove duplicates
                all_tags = list(dict.fromkeys(all_tags))
                
                if all_tags:
                    print(f"Adding {len(all_tags)} tags...")
                    tag_result = await self._add_tags(client, product_id, all_tags)
                    if not tag_result["success"]:
                        print(f"Warning: Failed to add tags: {tag_result['error']}")
            
            # Step 5: Publish to channels
            print("Publishing to channels...")
            publish_result = await self._publish_to_channels(client, product_id)
            if not publish_result["success"]:
                print(f"Warning: Failed to publish: {publish_result['error']}")
            
            # Get shop URL for admin link
            shop_url = os.getenv('SHOPIFY_SHOP_URL', '').replace('https://', '')
            product_admin_id = product_id.split('/')[-1]
            
            return {
                "success": True,
                "product_id": product_id,
                "title": title,
                "admin_url": f"https://{shop_url}/admin/products/{product_admin_id}",
                "variant_id": variant_id,
                "inventory_item_id": inventory_item_id,
                "metafields_added": len(metafields),
                "tags_added": len(all_tags) if auto_tags or tags else 0,
                "published_to_channels": publish_result.get("channel_count", 0)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _create_product(self, client: ShopifyClient, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create basic product"""
        mutation = """
        mutation createProduct($input: ProductInput!) {
            productCreate(input: $input) {
                product {
                    id
                    title
                    handle
                    variants(first: 1) {
                        edges {
                            node {
                                id
                                inventoryItem {
                                    id
                                }
                            }
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {"input": product_data}
        result = client.execute_graphql(mutation, variables)
        
        if 'errors' in result:
            return {"success": False, "error": f"GraphQL errors: {result['errors']}"}
        
        product_response = result['data']['productCreate']
        if product_response['userErrors']:
            return {"success": False, "error": f"User errors: {product_response['userErrors']}"}
        
        product = product_response['product']
        variant = product['variants']['edges'][0]['node']
        
        return {
            "success": True,
            "product_id": product['id'],
            "variant_id": variant['id'],
            "inventory_item_id": variant['inventoryItem']['id'],
            "handle": product['handle']
        }
    
    async def _update_variant_details(self, client: ShopifyClient, product_id: str, variant_id: str,
                                     inventory_item_id: str, sku: Optional[str] = None,
                                     cost: Optional[str] = None, weight: Optional[float] = None,
                                     price: Optional[str] = None, compare_at_price: Optional[str] = None) -> Dict[str, Any]:
        """Update variant details"""
        mutation = """
        mutation updateVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                productVariants {
                    id
                    sku
                    price
                    inventoryItem {
                        unitCost {
                            amount
                        }
                        measurement {
                            weight {
                                value
                                unit
                            }
                        }
                        tracked
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variant_input = {
            "id": variant_id,
            "inventoryPolicy": "DENY",  # Always set to DENY
            "inventoryItem": {
                "tracked": True  # Always enable tracking
            }
        }
        
        if sku:
            variant_input["inventoryItem"]["sku"] = sku
        
        if cost:
            variant_input["inventoryItem"]["cost"] = cost
        
        if weight:
            variant_input["inventoryItem"]["measurement"] = {
                "weight": {
                    "value": weight,
                    "unit": "GRAMS"
                }
            }
        
        if price:
            variant_input["price"] = price
        
        if compare_at_price:
            variant_input["compareAtPrice"] = compare_at_price
        
        variables = {
            "productId": product_id,
            "variants": [variant_input]
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
            errors = result['data']['productVariantsBulkUpdate']['userErrors']
            return {"success": False, "error": f"Variant update errors: {errors}"}
        
        return {"success": True}
    
    async def _add_metafields(self, client: ShopifyClient, product_id: str, metafields: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Add metafields to product"""
        mutation = """
        mutation updateProduct($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "input": {
                "id": product_id,
                "metafields": metafields
            }
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productUpdate', {}).get('userErrors'):
            errors = result['data']['productUpdate']['userErrors']
            return {"success": False, "error": f"Metafield errors: {errors}"}
        
        return {"success": True}
    
    async def _add_tags(self, client: ShopifyClient, product_id: str, tags: List[str]) -> Dict[str, Any]:
        """Add tags to product"""
        mutation = """
        mutation addTags($id: ID!, $tags: [String!]!) {
            tagsAdd(id: $id, tags: $tags) {
                node {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "id": product_id,
            "tags": tags
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('tagsAdd', {}).get('userErrors'):
            errors = result['data']['tagsAdd']['userErrors']
            return {"success": False, "error": f"Tag errors: {errors}"}
        
        return {"success": True}
    
    async def _publish_to_channels(self, client: ShopifyClient, product_id: str) -> Dict[str, Any]:
        """Publish product to all sales channels"""
        channels = [
            "gid://shopify/Channel/46590273",     # Online Store
            "gid://shopify/Channel/46590337",     # Point of Sale
            "gid://shopify/Channel/22067970082",  # Google & YouTube
            "gid://shopify/Channel/44906577954",  # Facebook & Instagram
            "gid://shopify/Channel/93180952610",  # Shop
            "gid://shopify/Channel/231226015778", # Hydrogen
            "gid://shopify/Channel/231226048546", # Hydrogen
            "gid://shopify/Channel/231776157730", # Hydrogen
            "gid://shopify/Channel/255970312226"  # Attentive
        ]
        
        mutation = """
        mutation publishProduct($input: ProductPublishInput!) {
            productPublish(input: $input) {
                product {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        publications = [{"channelId": channel_id} for channel_id in channels]
        
        variables = {
            "input": {
                "id": product_id,
                "productPublications": publications
            }
        }
        
        result = client.execute_graphql(mutation, variables)
        
        if result.get('data', {}).get('productPublish', {}).get('userErrors'):
            errors = result['data']['productPublish']['userErrors']
            return {"success": False, "error": f"Publishing errors: {errors}"}
        
        return {"success": True, "channel_count": len(channels)}
    
    def _build_metafields(self, buybox: Optional[str] = None, faqs: Optional[List[Dict[str, str]]] = None,
                         tech_specs: Optional[Dict[str, Any]] = None, variant_preview: Optional[str] = None,
                         sale_end: Optional[str] = None, seasonal: Optional[bool] = None,
                         product_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Build metafields list"""
        metafields = []
        
        if buybox:
            metafields.append({
                "namespace": "buybox",
                "key": "content",
                "value": buybox,
                "type": "multi_line_text_field"
            })
        
        if faqs:
            # Wrap in proper structure
            faqs_json = json.dumps({"faqs": faqs})
            metafields.append({
                "namespace": "faq",
                "key": "content",
                "value": faqs_json,
                "type": "json"
            })
        
        if tech_specs:
            metafields.append({
                "namespace": "specs",
                "key": "techjson",
                "value": json.dumps(tech_specs),
                "type": "json"
            })
        
        if variant_preview:
            metafields.append({
                "namespace": "ext",
                "key": "variantPreviewName",
                "value": variant_preview,
                "type": "single_line_text_field"
            })
        
        if sale_end:
            metafields.append({
                "namespace": "inventory",
                "key": "ShappifySaleEndDate",
                "value": sale_end,
                "type": "single_line_text_field"
            })
        
        if seasonal and product_type == "Fresh Coffee":
            metafields.append({
                "namespace": "coffee",
                "key": "seasonality",
                "value": "true",
                "type": "boolean"
            })
        
        return metafields
    
    def _get_product_type_tags(self, product_type: str) -> List[str]:
        """Get standard tags based on product type"""
        type_tags = {
            "Espresso Machines": ["espresso-machines", "Espresso Machines", "consumer"],
            "Grinders": ["grinders", "grinder", "consumer", "burr-grinder"],
            "Fresh Coffee": ["NC_FreshCoffee", "coffee"],
            "Accessories": ["accessories", "WAR-ACC"],
            "Parts": ["WAR-PAR"],
            "Cleaning": ["NC_Cleaning", "WAR-CON"]
        }
        return type_tags.get(product_type, [])
    
    def _get_vendor_tags(self, vendor: str, product_type: str) -> List[str]:
        """Get vendor-specific tags"""
        vendor_lower = vendor.lower()
        tags = [vendor_lower]
        
        # VIM vendors for machines/grinders
        vim_vendors = ["ascaso", "bezzera", "bellezza", "ecm", "gaggia", "profitec", 
                       "magister", "quick mill", "coffee brain", "jura", "sanremo", "rancilio"]
        
        if vendor_lower in vim_vendors and product_type in ["Espresso Machines", "Grinders"]:
            tags.extend(["VIM", "WAR-VIM"])
        
        return tags
    
    async def test(self) -> Dict[str, Any]:
        """Test the tool with validation"""
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