#!/usr/bin/env python3
"""
Create an open box listing from an existing product.

This tool creates an open box version of an existing product following
iDrinkCoffee.com conventions:
- SKU: OB-{YYMM}-{Serial}-{OriginalSKU}
- Title: {Original Title} |{Serial}| - {Condition}
- Tags: Adds open-box, ob-YYMM tags
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Optional, Any
from base import ShopifyClient

def find_product(client: ShopifyClient, identifier: str) -> Optional[Dict[str, Any]]:
    """Find a product by various identifiers."""
    # Try different search methods
    searches = [
        f'sku:"{identifier}"',
        f'handle:"{identifier}"',
        f'title:"{identifier}"',
        f'"{identifier}"'
    ]
    
    for search_query in searches:
        query = """
        query searchProducts($query: String!) {
            products(first: 5, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        vendor
                        productType
                        status
                        tags
                        description
                        seo {
                            title
                            description
                        }
                        priceRangeV2 {
                            minVariantPrice {
                                amount
                                currencyCode
                            }
                        }
                        variants(first: 10) {
                            edges {
                                node {
                                    id
                                    title
                                    sku
                                    price
                                    compareAtPrice
                                    inventoryItem {
                                        id
                                        unitCost {
                                            amount
                                        }
                                    }
                                    weight
                                    weightUnit
                                }
                            }
                        }
                        metafields(first: 20) {
                            edges {
                                node {
                                    namespace
                                    key
                                    value
                                    type
                                }
                            }
                        }
                        media(first: 20) {
                            edges {
                                node {
                                    ... on MediaImage {
                                        id
                                        alt
                                        image {
                                            url
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = client.execute_graphql(query, {"query": search_query})
        
        products = result.get('data', {}).get('products', {}).get('edges', [])
        if products:
            # Try to find exact match by SKU if searching by SKU
            if search_query.startswith('sku:'):
                for edge in products:
                    product = edge['node']
                    for variant_edge in product.get('variants', {}).get('edges', []):
                        if variant_edge['node']['sku'] == identifier:
                            return product
            
            # Otherwise return the first result
            return products[0]['node']
    
    # Try by numeric ID
    if identifier.isdigit():
        gid = f"gid://shopify/Product/{identifier}"
        query = """
        query getProduct($id: ID!) {
            product(id: $id) {
                id
                title
                handle
                vendor
                productType
                status
                tags
                description
                seo {
                    title
                    description
                }
                priceRangeV2 {
                    minVariantPrice {
                        amount
                        currencyCode
                    }
                }
                variants(first: 10) {
                    edges {
                        node {
                            id
                            title
                            sku
                            price
                            compareAtPrice
                            inventoryItem {
                                id
                                unitCost {
                                    amount
                                }
                            }
                            weight
                            weightUnit
                        }
                    }
                }
                metafields(first: 20) {
                    edges {
                        node {
                            namespace
                            key
                            value
                            type
                        }
                    }
                }
                media(first: 20) {
                    edges {
                        node {
                            ... on MediaImage {
                                id
                                alt
                                image {
                                    url
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        result = client.execute_graphql(query, {"id": gid})
        product = result.get('data', {}).get('product')
        if product:
            return product
    
    return None

def create_open_box_product(client: ShopifyClient, original: Dict[str, Any], 
                          serial: str, condition: str, 
                          price: Optional[float] = None,
                          discount_pct: Optional[float] = None,
                          note: Optional[str] = None) -> Dict[str, Any]:
    """Create an open box version of a product using productDuplicate."""
    
    # Get current date for SKU and tag
    now = datetime.now()
    yymm = now.strftime("%y%m")
    
    # Get original variant (first one)
    original_variant = original['variants']['edges'][0]['node']
    original_sku = original_variant['sku'] or "NOSKU"
    original_price = float(original_variant['price'])
    
    # Calculate open box price
    if price:
        ob_price = price
    elif discount_pct:
        ob_price = original_price * (1 - discount_pct / 100)
    else:
        # Default 10% discount
        ob_price = original_price * 0.9
    
    # Create SKU and title
    ob_sku = f"OB-{yymm}-{serial}-{original_sku}"
    ob_title = f"{original['title']} |{serial}| - {condition}"
    
    # First, duplicate the product
    mutation = """
    mutation duplicateProduct($productId: ID!, $newTitle: String!, $newStatus: ProductStatus) {
        productDuplicate(productId: $productId, newTitle: $newTitle, newStatus: $newStatus, includeImages: true) {
            newProduct {
                id
                title
                handle
                variants(first: 10) {
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
    
    variables = {
        "productId": original['id'],
        "newTitle": ob_title,
        "newStatus": "DRAFT"
    }
    
    result = client.execute_graphql(mutation, variables)
    
    if result.get('data', {}).get('productDuplicate', {}).get('userErrors'):
        errors = result['data']['productDuplicate']['userErrors']
        raise Exception(f"Failed to duplicate product: {errors}")
    
    product = result['data']['productDuplicate']['newProduct']
    product_id = product['id']
    # Now update the duplicated product with open box details
    
    # Build description with note if provided
    if note:
        update_description = True
        new_description = f"<p><strong>Open Box Note:</strong> {note}</p>\n{original.get('description', '')}"
    else:
        update_description = False
        new_description = None
    
    # Update product details including description and SEO
    if update_description or original.get('seo'):
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
        
        update_input = {"id": product_id}
        
        if update_description:
            update_input["descriptionHtml"] = new_description
            
        if original.get('seo'):
            update_input['seo'] = {
                "title": f"{original['seo'].get('title', original['title'])} - Open Box {serial}",
                "description": original['seo'].get('description', '')
            }
        
        variables = {"input": update_input}
        client.execute_graphql(mutation, variables)
    
    # Add open box tags
    tags_to_add = ['open-box', f'ob-{yymm}']
    mutation = """
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
    """
    
    variables = {
        "id": product_id,
        "tags": tags_to_add
    }
    
    client.execute_graphql(mutation, variables)
    
    # Update variant details (SKU and price)
    if product['variants']['edges']:
        variant = product['variants']['edges'][0]['node']
        variant_id = variant['id']
        
        # Update SKU and price using productVariantsBulkUpdate
        mutation = """
        mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                productVariants {
                    id
                    sku
                    price
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variables = {
            "productId": product_id,
            "variants": [{
                "id": variant_id,
                "sku": ob_sku,
                "price": str(ob_price)
            }]
        }
        
        result = client.execute_graphql(mutation, variables)
        if result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
            errors = result['data']['productVariantsBulkUpdate']['userErrors']
            print(f"Warning: Failed to update variant: {errors}")
    
    return product

def main():
    parser = argparse.ArgumentParser(
        description="Create an open box listing from an existing product",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create with automatic 10% discount
  %(prog)s --identifier "EC685M" --serial "ABC123" --condition "Excellent"
  
  # Create with specific price
  %(prog)s --identifier "7234567890123" --serial "XYZ789" --condition "Good" --price 899.99
  
  # Create with percentage discount
  %(prog)s --identifier "delonghi-dedica" --serial "DEF456" --condition "Scratch & Dent" --discount 20
  
  # Add a note
  %(prog)s --identifier "BES870XL" --serial "GHI789" --condition "Excellent" --discount 15 --note "Minor scratches on drip tray"
        """
    )
    
    parser.add_argument('--identifier', '-i', required=True,
                       help='Product identifier (SKU, handle, title, or numeric ID)')
    parser.add_argument('--serial', '-s', required=True,
                       help='Serial number for the open box unit')
    parser.add_argument('--condition', '-c', required=True,
                       help='Condition description (e.g., Excellent, Good, Fair, Scratch & Dent)')
    parser.add_argument('--price', '-p', type=float,
                       help='Specific price for the open box item')
    parser.add_argument('--discount', '-d', type=float, dest='discount_pct',
                       help='Percentage discount from original price (e.g., 15 for 15%)')
    parser.add_argument('--note', '-n',
                       help='Additional note to add to the product description')
    parser.add_argument('--publish', action='store_true',
                       help='Publish the product immediately (default: draft)')
    
    args = parser.parse_args()
    
    # Initialize client
    client = ShopifyClient()
    
    try:
        # Find the original product
        print(f"Finding product: {args.identifier}...")
        original = find_product(client, args.identifier)
        
        if not original:
            print(f"Error: Product not found with identifier: {args.identifier}")
            sys.exit(1)
        
        print(f"Found: {original['title']} (SKU: {original['variants']['edges'][0]['node']['sku']})")
        
        # Create the open box listing
        print(f"Creating open box listing...")
        product = create_open_box_product(
            client, 
            original,
            args.serial,
            args.condition,
            args.price,
            args.discount_pct,
            args.note
        )
        
        print(f"\n✅ Successfully created open box listing!")
        print(f"   Title: {product['title']}")
        print(f"   Handle: {product['handle']}")
        print(f"   ID: {product['id']}")
        print(f"   Admin URL: https://idrinkcoffee.myshopify.com/admin/products/{product['id'].split('/')[-1]}")
        
        # Publish if requested
        if args.publish:
            mutation = """
            mutation publishProduct($id: ID!) {
                productUpdate(input: {id: $id, status: ACTIVE}) {
                    product {
                        id
                        status
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """
            
            result = client.execute_graphql(mutation, {"id": product['id']})
            if result.get('data', {}).get('productUpdate', {}).get('userErrors'):
                print(f"Warning: Failed to publish product")
            else:
                print(f"   Status: Published")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()