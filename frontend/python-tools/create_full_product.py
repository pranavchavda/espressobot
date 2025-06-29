#!/usr/bin/env python3
"""
Create a complete product with all metafields, tags, and proper configuration.

This tool creates a fully-configured product following iDrinkCoffee.com conventions,
including all necessary metafields, tags, and inventory settings.
"""

import os
import sys
import json
import argparse
from typing import Dict, List, Optional, Any
from base import ShopifyClient

def create_product(client: ShopifyClient, product_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create product with basic information."""
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
    return client.execute_graphql(mutation, variables)

def update_variant_details(client: ShopifyClient, product_id: str, variant_id: str, 
                         inventory_item_id: str, sku: Optional[str] = None, cost: Optional[str] = None,
                         weight: Optional[float] = None) -> None:
    """Update variant SKU, cost, and weight in a single mutation."""
    if not any([sku, cost, weight]):
        return
        
    # Use productVariantsBulkUpdate to update everything in one call
    mutation = """
    mutation updateVariant($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            productVariants {
                id
                sku
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
        "inventoryItem": {
            "tracked": True  # Always enable inventory tracking
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
    
    variables = {
        "productId": product_id,
        "variants": [variant_input]
    }
    
    result = client.execute_graphql(mutation, variables)
    if result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
        errors = result['data']['productVariantsBulkUpdate']['userErrors']
        print(f"Warning: Failed to update variant details: {errors}")

def add_metafields(client: ShopifyClient, product_id: str, metafields: List[Dict[str, Any]]) -> None:
    """Add metafields to product."""
    if not metafields:
        return
        
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
        print(f"Warning: Failed to add some metafields: {errors}")

def add_tags(client: ShopifyClient, product_id: str, tags: List[str]) -> None:
    """Add tags to product using tagsAdd mutation."""
    if not tags:
        return
        
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
        print(f"Warning: Failed to add tags: {errors}")

def update_inventory_settings(client: ShopifyClient, inventory_item_id: str, 
                            tracked: bool = True, policy: str = "DENY") -> None:
    """Update inventory tracking and policy settings."""
    mutation = """
    mutation updateInventoryItem($id: ID!, $input: InventoryItemUpdateInput!) {
        inventoryItemUpdate(id: $id, input: $input) {
            inventoryItem {
                id
                tracked
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {
        "id": inventory_item_id,
        "input": {
            "tracked": tracked
        }
    }
    
    result = client.execute_graphql(mutation, variables)
    if result.get('data', {}).get('inventoryItemUpdate', {}).get('userErrors'):
        errors = result['data']['inventoryItemUpdate']['userErrors']
        print(f"Warning: Failed to update inventory settings: {errors}")

def publish_to_channels(client: ShopifyClient, product_id: str) -> None:
    """Publish product to all relevant channels."""
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
        print(f"Warning: Failed to publish to some channels: {errors}")
    else:
        print(f"✓ Published to {len(channels)} channels")

def get_product_type_tags(product_type: str) -> List[str]:
    """Get standard tags based on product type."""
    type_tags = {
        "Espresso Machines": ["espresso-machines", "Espresso Machines"],
        "Grinders": ["grinders", "grinder"],
        "Fresh Coffee": ["NC_FreshCoffee", "coffee"],
        "Accessories": ["accessories", "WAR-ACC"],
        "Parts": ["WAR-PAR"],
        "Cleaning": ["NC_Cleaning", "WAR-CON"]
    }
    return type_tags.get(product_type, [])

def get_vendor_tags(vendor: str, product_type: str) -> List[str]:
    """Get vendor-specific tags."""
    vendor_lower = vendor.lower()
    tags = [vendor_lower]
    
    # VIM vendors for machines/grinders
    vim_vendors = ["ascaso", "bezzera", "bellezza", "ecm", "gaggia", "profitec", 
                   "magister", "quick mill", "coffee brain", "jura", "sanremo", "rancilio"]
    
    if vendor_lower in vim_vendors and product_type in ["Espresso Machines", "Grinders"]:
        tags.extend(["VIM", "WAR-VIM"])
    
    return tags

def parse_json_file(file_path: str) -> Dict[str, Any]:
    """Parse JSON configuration file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Create a complete product with all metafields and proper configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic product
  %(prog)s --title "Breville Barista Express" --vendor "Breville" --type "Espresso Machines" \\
    --price "699.99" --sku "BES870XL" --cost "450.00"

  # With metafields
  %(prog)s --title "DeLonghi Dedica" --vendor "DeLonghi" --type "Espresso Machines" \\
    --price "249.99" --sku "EC685M" --cost "150.00" \\
    --buybox "Experience café-quality espresso in a compact design..."

  # Coffee product
  %(prog)s --title "Ethiopia Yirgacheffe" --vendor "Escarpment Coffee Roasters" \\
    --type "Fresh Coffee" --price "24.99" --sku "ETH-YIRG-001" \\
    --tags "ROAST-Light,REGION-Yirgacheffe,NOTES-Floral#Citrus#Tea-like" \\
    --seasonal

  # From JSON file
  %(prog)s --from-json product_config.json

JSON file format:
{
  "title": "Product Name",
  "vendor": "Brand",
  "productType": "Espresso Machines",
  "price": "999.99",
  "sku": "SKU123",
  "cost": "600.00",
  "weight": 15000,
  "description": "Product description...",
  "buybox": "Sales pitch...",
  "faqs": [{"question": "Q?", "answer": "A."}],
  "techSpecs": {"manufacturer": "Brand", "power": "1200W"},
  "tags": ["additional-tag"],
  "status": "DRAFT"
}
        """
    )
    
    # Product basics
    parser.add_argument('--title', help='Product title')
    parser.add_argument('--vendor', help='Product vendor/brand')
    parser.add_argument('--type', dest='product_type', help='Product type')
    parser.add_argument('--description', help='Product description (HTML)')
    parser.add_argument('--handle', help='URL handle (auto-generated if not provided)')
    
    # Variant details
    parser.add_argument('--price', help='Product price')
    parser.add_argument('--sku', help='Product SKU')
    parser.add_argument('--cost', help='Cost of goods (COGS)')
    parser.add_argument('--weight', type=float, help='Product weight in grams')
    parser.add_argument('--compare-at', help='Compare at price')
    
    # Metafields
    parser.add_argument('--buybox', help='Buy box content')
    parser.add_argument('--faqs', help='FAQs JSON array')
    parser.add_argument('--tech-specs', help='Technical specifications JSON')
    parser.add_argument('--variant-preview', help='Variant preview name (e.g., "Black")')
    parser.add_argument('--sale-end', help='Sale end date (ISO format)')
    
    # Coffee-specific
    parser.add_argument('--seasonal', action='store_true', help='Mark as seasonal coffee')
    
    # Tags and status
    parser.add_argument('--tags', help='Additional tags (comma-separated)')
    parser.add_argument('--status', choices=['DRAFT', 'ACTIVE'], default='DRAFT',
                       help='Product status (default: DRAFT)')
    parser.add_argument('--no-auto-tags', action='store_true', 
                       help='Skip automatic tag generation')
    
    # Configuration
    parser.add_argument('--from-json', help='Load all settings from JSON file')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be created without making changes')
    
    args = parser.parse_args()
    
    # Load from JSON if provided
    if args.from_json:
        config = parse_json_file(args.from_json)
        # Override with any command-line arguments
        for key, value in vars(args).items():
            if value is not None and key not in ['from_json', 'dry_run']:
                config[key] = value
    else:
        config = vars(args)
        # Require minimum fields
        if not all([args.title, args.vendor, args.product_type, args.price]):
            parser.error("--title, --vendor, --type, and --price are required")
    
    # Initialize client
    client = ShopifyClient()
    
    # Build product data
    product_data = {
        "title": config.get('title'),
        "vendor": config.get('vendor'),
        "productType": config.get('product_type') or config.get('productType'),
        "status": config.get('status', 'DRAFT')
    }
    
    if config.get('description'):
        product_data['descriptionHtml'] = config['description']
    
    if config.get('handle'):
        product_data['handle'] = config['handle']
    
    # Build tags list
    tags = []
    if not config.get('no_auto_tags'):
        # Add product type tags
        tags.extend(get_product_type_tags(product_data['productType']))
        # Add vendor tags
        tags.extend(get_vendor_tags(product_data['vendor'], product_data['productType']))
        # Add standard tags based on type
        if product_data['productType'] == 'Espresso Machines':
            tags.append('consumer')
        elif product_data['productType'] == 'Grinders':
            tags.extend(['consumer', 'burr-grinder'])
    
    # Add custom tags
    if config.get('tags'):
        if isinstance(config['tags'], str):
            tags.extend([t.strip() for t in config['tags'].split(',') if t.strip()])
        else:
            tags.extend(config['tags'])
    
    # Remove duplicates while preserving order
    seen = set()
    tags = [x for x in tags if not (x in seen or seen.add(x))]
    
    if args.dry_run:
        print("DRY RUN - Would create product with:")
        print(f"\nBasic Info:")
        print(f"  Title: {product_data['title']}")
        print(f"  Vendor: {product_data['vendor']}")
        print(f"  Type: {product_data['productType']}")
        print(f"  Status: {product_data['status']}")
        
        print(f"\nVariant:")
        print(f"  Price: ${config.get('price')}")
        print(f"  SKU: {config.get('sku', 'Not set')}")
        print(f"  Cost: ${config.get('cost', 'Not set')}")
        print(f"  Weight: {config.get('weight', 'Not set')}g")
        
        print(f"\nTags: {', '.join(tags)}")
        
        if any([config.get(k) for k in ['buybox', 'faqs', 'tech_specs']]):
            print("\nMetafields:")
            if config.get('buybox'):
                print(f"  Buy Box: {config['buybox'][:50]}...")
            if config.get('faqs'):
                print(f"  FAQs: {config['faqs'][:50]}...")
            if config.get('tech_specs'):
                print(f"  Tech Specs: {config['tech_specs'][:50]}...")
        
        return
    
    print(f"Creating product: {product_data['title']}...")
    
    # Create product
    result = create_product(client, product_data)
    
    if 'errors' in result:
        print(f"Error creating product: {result['errors']}")
        sys.exit(1)
    
    product_response = result['data']['productCreate']
    if product_response['userErrors']:
        print(f"Error: {product_response['userErrors']}")
        sys.exit(1)
    
    product = product_response['product']
    product_id = product['id']
    print(f"✓ Created product: {product['title']} (ID: {product_id})")
    
    # Get variant and inventory item IDs
    variant = product['variants']['edges'][0]['node']
    variant_id = variant['id']
    inventory_item_id = variant['inventoryItem']['id']
    
    # Update variant details (price is set in a separate step)
    if any([config.get('sku'), config.get('cost'), config.get('weight')]):
        print("Updating variant details...")
        update_variant_details(
            client, product_id, variant_id, inventory_item_id,
            sku=config.get('sku'),
            cost=config.get('cost'),
            weight=config.get('weight')
        )
        print("✓ Updated variant details")
    
    # Update variant price and inventory policy
    if config.get('price') or config.get('compare_at') or True:  # Always update to set inventory policy
        print("Updating variant price and inventory policy...")
        mutation = """
        mutation updateVariantPrice($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
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
        """
        
        variant_update = {
            "id": variant_id,
            "inventoryPolicy": "DENY"  # Always set inventory policy to DENY
        }
        if config.get('price'):
            variant_update['price'] = config['price']
        if config.get('compare_at'):
            variant_update['compareAtPrice'] = config['compare_at']
            
        variables = {
            "productId": product_id,
            "variants": [variant_update]
        }
        
        result = client.execute_graphql(mutation, variables)
        if result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
            errors = result['data']['productVariantsBulkUpdate']['userErrors']
            print(f"Warning: Failed to update price: {errors}")
        else:
            print("✓ Updated variant price")
    
    # Add metafields
    metafields = []
    
    if config.get('buybox'):
        metafields.append({
            "namespace": "buybox",
            "key": "content",
            "value": config['buybox'],
            "type": "multi_line_text_field"
        })
    
    
    if config.get('faqs'):
        # Ensure proper JSON structure with "faqs" key
        if isinstance(config['faqs'], str):
            try:
                faqs_data = json.loads(config['faqs'])
            except json.JSONDecodeError:
                print("Warning: Invalid FAQs JSON format")
                faqs_data = []
        else:
            faqs_data = config['faqs']
        
        # Wrap in proper structure if needed
        if isinstance(faqs_data, list):
            faqs_json = json.dumps({"faqs": faqs_data})
        elif isinstance(faqs_data, dict) and 'faqs' in faqs_data:
            faqs_json = json.dumps(faqs_data)
        else:
            faqs_json = json.dumps({"faqs": faqs_data})
            
        metafields.append({
            "namespace": "faq",
            "key": "content",
            "value": faqs_json,
            "type": "json"
        })
    
    if config.get('tech_specs') or config.get('techSpecs'):
        specs = config.get('tech_specs') or config.get('techSpecs')
        specs_json = specs if isinstance(specs, str) else json.dumps(specs)
        metafields.append({
            "namespace": "specs",
            "key": "techjson",
            "value": specs_json,
            "type": "json"
        })
    
    if config.get('variant_preview') or config.get('variantPreview'):
        metafields.append({
            "namespace": "ext",
            "key": "variantPreviewName",
            "value": config.get('variant_preview') or config.get('variantPreview'),
            "type": "single_line_text_field"
        })
    
    if config.get('sale_end') or config.get('saleEnd'):
        metafields.append({
            "namespace": "inventory",
            "key": "ShappifySaleEndDate",
            "value": config.get('sale_end') or config.get('saleEnd'),
            "type": "single_line_text_field"
        })
    
    if config.get('seasonal') and product_data['productType'] == 'Fresh Coffee':
        metafields.append({
            "namespace": "coffee",
            "key": "seasonality",
            "value": "true",
            "type": "boolean"
        })
    
    if metafields:
        print(f"Adding {len(metafields)} metafields...")
        add_metafields(client, product_id, metafields)
        print("✓ Added metafields")
    
    # Add tags
    if tags:
        print(f"Adding {len(tags)} tags...")
        add_tags(client, product_id, tags)
        print("✓ Added tags")
    
    # Inventory settings are already updated in variant details
    
    # Publish to channels (product remains in DRAFT status)
    print("Publishing to channels...")
    publish_to_channels(client, product_id)
    
    print(f"\n✅ Successfully created product!")
    print(f"   ID: {product_id}")
    print(f"   Handle: {product.get('handle', 'N/A')}")
    print(f"   Admin URL: https://{os.getenv('SHOPIFY_SHOP_URL', '').replace('https://', '')}/admin/products/{product_id.split('/')[-1]}")
    print(f"\n💡 To add product features, use: python tools/manage_features_metaobjects.py --product \"{product_id.split('/')[-1]}\" --add \"Feature Title\" \"Feature description\"")

if __name__ == "__main__":
    main()