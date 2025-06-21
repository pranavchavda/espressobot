#!/usr/bin/env python3
"""
Create machine+grinder combo products

Creates a combo product by duplicating the first product and combining it with the second.
Automatically generates combo images, pricing, and manages all product data.

Examples:
    # Create combo using product handles
    python tools/create_combo.py --product1 breville-barista-express --product2 eureka-mignon-specialita --discount 200

    # Create combo using SKUs with percentage discount
    python tools/create_combo.py --product1 BES870XL --product2 EUREKA-SPEC --discount-percent 15

    # Create combo with specific SKU suffix and publish immediately
    python tools/create_combo.py --product1 7234567890123 --product2 9876543210987 --sku-suffix A1 --publish

    # Create multiple combos from CSV file
    python tools/create_combo.py --from-csv combos.csv
"""

import os
import sys
import json
import argparse
import requests
import csv
from io import BytesIO
from PIL import Image
import numpy as np
import base64
import uuid
from datetime import datetime
from pathlib import Path

from base import ShopifyClient

def get_product_details(client, identifier):
    """Get product details including variants and images"""
    product_id = client.resolve_product_id(identifier)
    if not product_id:
        print(f"Error: Could not find product with identifier: {identifier}")
        return None
    
    query = '''
    query getProduct($id: ID!) {
        product(id: $id) {
            id
            title
            handle
            descriptionHtml
            vendor
            productType
            tags
            images(first: 10) {
                edges {
                    node {
                        id
                        url
                        altText
                    }
                }
            }
            variants(first: 1) {
                edges {
                    node {
                        id
                        price
                        compareAtPrice
                        sku
                        inventoryPolicy
                        inventoryItem {
                            unitCost {
                                amount
                            }
                        }
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
        }
    }
    '''
    
    variables = {"id": product_id}
    result = client.execute_graphql(query, variables)
    
    if result and 'data' in result and result['data'].get('product'):
        return result['data']['product']
    
    return None

def create_combo_image(image1_url, image2_url):
    """Create a combined image from two product images"""
    try:
        # Download images
        response1 = requests.get(image1_url)
        response2 = requests.get(image2_url)
        
        if response1.status_code != 200 or response2.status_code != 200:
            print("Error downloading images")
            return None
        
        # Open images
        img1 = Image.open(BytesIO(response1.content)).convert("RGBA")
        img2 = Image.open(BytesIO(response2.content)).convert("RGBA")
        
        # Trim whitespace
        img1 = trim_image(img1)
        img2 = trim_image(img2)
        
        # Calculate target dimensions (maintain aspect ratios)
        target_height = 800  # Standard height
        
        # Resize maintaining aspect ratio
        ratio1 = target_height / img1.height
        new_width1 = int(img1.width * ratio1)
        img1 = img1.resize((new_width1, target_height), Image.Resampling.LANCZOS)
        
        ratio2 = target_height / img2.height
        new_width2 = int(img2.width * ratio2)
        img2 = img2.resize((new_width2, target_height), Image.Resampling.LANCZOS)
        
        # Create new image with white background
        total_width = new_width1 + new_width2 + 50  # 50px gap
        combo_img = Image.new('RGBA', (total_width, target_height), (255, 255, 255, 255))
        
        # Paste images
        combo_img.paste(img1, (0, 0), img1 if img1.mode == 'RGBA' else None)
        combo_img.paste(img2, (new_width1 + 50, 0), img2 if img2.mode == 'RGBA' else None)
        
        # Convert to RGB for JPEG
        rgb_img = Image.new('RGB', combo_img.size, (255, 255, 255))
        rgb_img.paste(combo_img, mask=combo_img.split()[3] if combo_img.mode == 'RGBA' else None)
        
        return rgb_img
        
    except Exception as e:
        print(f"Error creating combo image: {e}")
        return None

def trim_image(image):
    """Remove excess whitespace from image"""
    # Convert to numpy array
    np_image = np.array(image)
    
    # Find non-white pixels (considering alpha channel if present)
    if image.mode == 'RGBA':
        # For RGBA, consider both color and alpha
        mask = (np_image[:,:,3] > 0) & ((np_image[:,:,0] < 250) | (np_image[:,:,1] < 250) | (np_image[:,:,2] < 250))
    else:
        # For RGB, just check color values
        mask = (np_image[:,:,0] < 250) | (np_image[:,:,1] < 250) | (np_image[:,:,2] < 250)
    
    # Find bounding box
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    
    if not np.any(rows) or not np.any(cols):
        return image  # Return original if all white
    
    # Get bounds with small padding
    y_min, y_max = np.where(rows)[0][[0, -1]]
    x_min, x_max = np.where(cols)[0][[0, -1]]
    
    # Add 10px padding
    padding = 10
    y_min = max(0, y_min - padding)
    y_max = min(image.height, y_max + padding)
    x_min = max(0, x_min - padding)
    x_max = min(image.width, x_max + padding)
    
    return image.crop((x_min, y_min, x_max, y_max))

def create_staged_upload(client, filename, file_size, mime_type):
    """Create a staged upload target for a file."""
    mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
        stagedUploadsCreate(input: $input) {
            stagedTargets {
                resourceUrl
                url
                parameters {
                    name
                    value
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
        "input": [{
            "filename": filename,
            "mimeType": mime_type,
            "fileSize": str(file_size),
            "httpMethod": "POST",
            "resource": "FILE"
        }]
    }
    
    result = client.execute_graphql(mutation, variables)
    
    if result.get('data', {}).get('stagedUploadsCreate', {}).get('userErrors'):
        errors = result['data']['stagedUploadsCreate']['userErrors']
        raise Exception(f"Staged upload error: {errors}")
    
    targets = result.get('data', {}).get('stagedUploadsCreate', {}).get('stagedTargets', [])
    if not targets:
        raise Exception("No staged upload target created")
    
    return targets[0]

def upload_to_staged_target(target, file_content, filename):
    """Upload file content to the staged target."""
    # Build form data with parameters
    files = []
    for param in target['parameters']:
        files.append((param['name'], (None, param['value'])))
    
    # Add the file
    files.append(('file', (filename, file_content)))
    
    # Upload to the staged URL
    response = requests.post(target['url'], files=files)
    response.raise_for_status()

def upload_combo_image(client, product_id, combo_image):
    """Upload combo image to product"""
    # Convert image to bytes
    buffer = BytesIO()
    combo_image.save(buffer, format='JPEG', quality=95)
    image_bytes = buffer.getvalue()
    
    # Create staged upload
    filename = f"combo_{uuid.uuid4().hex[:8]}.jpg"
    file_size = len(image_bytes)
    mime_type = "image/jpeg"
    
    try:
        # Create staged upload target
        target = create_staged_upload(client, filename, file_size, mime_type)
        
        # Upload to staged target
        upload_to_staged_target(target, image_bytes, filename)
        
        # Now create product media with the staged upload URL
        mutation = '''
        mutation createProductMedia($productId: ID!, $media: [CreateMediaInput!]!) {
            productCreateMedia(productId: $productId, media: $media) {
                media {
                    ... on MediaImage {
                        id
                        image {
                            url
                        }
                    }
                }
                mediaUserErrors {
                    field
                    message
                }
            }
        }
        '''
        
        variables = {
            "productId": product_id,
            "media": [{
                "alt": "Product Combo Image",
                "originalSource": target['resourceUrl'],
                "mediaContentType": "IMAGE"
            }]
        }
        
        result = client.execute_graphql(mutation, variables)
        if result and 'data' in result and result['data'].get('productCreateMedia'):
            if result['data']['productCreateMedia']['mediaUserErrors']:
                print(f"Error uploading image: {result['data']['productCreateMedia']['mediaUserErrors']}")
                return False
            print("✓ Combo image uploaded successfully")
            return True
    except Exception as e:
        print(f"Error uploading combo image: {e}")
        return False
    
    return False

def create_combo_listing(client, product1_id, product2_id, sku_suffix=None, discount_amount=None, 
                        discount_percent=None, price=None, publish=False, csv_writer=None):
    """Create a combo product listing"""
    
    # Get product details
    print(f"Fetching product 1 details...")
    product1 = get_product_details(client, product1_id)
    if not product1:
        return None
        
    print(f"Fetching product 2 details...")
    product2 = get_product_details(client, product2_id)
    if not product2:
        return None
    
    # Extract variant info
    variant1 = product1['variants']['edges'][0]['node'] if product1['variants']['edges'] else None
    variant2 = product2['variants']['edges'][0]['node'] if product2['variants']['edges'] else None
    
    if not variant1 or not variant2:
        print("Error: Products must have at least one variant")
        return None
    
    # Calculate pricing
    price1 = float(variant1['price'])
    price2 = float(variant2['price'])
    total_price = price1 + price2
    
    if price:
        combo_price = float(price)
    elif discount_amount:
        combo_price = max(total_price - discount_amount, 0.01)
    elif discount_percent:
        combo_price = max(total_price * (1 - discount_percent / 100), 0.01)
    else:
        combo_price = total_price
    
    # Calculate cost (if available)
    cost1 = float(variant1['inventoryItem']['unitCost']['amount']) if variant1['inventoryItem']['unitCost'] else 0
    cost2 = float(variant2['inventoryItem']['unitCost']['amount']) if variant2['inventoryItem']['unitCost'] else 0
    total_cost = cost1 + cost2 if (cost1 and cost2) else None
    
    # Generate combo title and SKU
    combo_title = f"{product1['title']} + {product2['title']} Combo"
    
    # Generate SKU
    if sku_suffix:
        combo_sku = f"COMBO-{datetime.now().strftime('%y%m')}-{sku_suffix}"
    else:
        # Use first 3 chars of each SKU or handle
        p1_code = (variant1['sku'][:3] if variant1['sku'] else product1['handle'][:3]).upper()
        p2_code = (variant2['sku'][:3] if variant2['sku'] else product2['handle'][:3]).upper()
        combo_sku = f"COMBO-{datetime.now().strftime('%y%m')}-{p1_code}-{p2_code}"
    
    print(f"\nCreating combo: {combo_title}")
    print(f"SKU: {combo_sku}")
    print(f"Price: ${combo_price:.2f} (was ${total_price:.2f})")
    
    # Step 1: Duplicate the first product
    mutation = '''
    mutation duplicateProduct($productId: ID!, $newTitle: String!, $includeImages: Boolean!, $newStatus: ProductStatus!) {
        productDuplicate(productId: $productId, newTitle: $newTitle, includeImages: $includeImages, newStatus: $newStatus) {
            newProduct {
                id
                title
                handle
            }
            userErrors {
                field
                message
            }
        }
    }
    '''
    
    variables = {
        "productId": product1['id'],
        "newTitle": combo_title,
        "includeImages": False,  # We'll add combo image
        "newStatus": "ACTIVE" if publish else "DRAFT"
    }
    
    result = client.execute_graphql(mutation, variables)
    if not result or 'data' not in result or not result['data'].get('productDuplicate'):
        print("Error: Failed to duplicate product")
        return None
    
    if result['data']['productDuplicate']['userErrors']:
        print(f"Error duplicating product: {result['data']['productDuplicate']['userErrors']}")
        return None
    
    new_product = result['data']['productDuplicate']['newProduct']
    print(f"Created combo product: {new_product['handle']}")
    
    # Step 2: Update the combo product with combined details
    # Combine tags
    tags1 = product1.get('tags', [])
    tags2 = product2.get('tags', [])
    combo_tags = list(set(tags1 + tags2 + ['combo', f'combo-{datetime.now().strftime("%y%m")}']))
    
    # Combine descriptions
    desc1 = product1.get('descriptionHtml', '')
    desc2 = product2.get('descriptionHtml', '')
    combo_description = f'''
    <div class="combo-description">
        <h3>This combo includes:</h3>
        <div class="combo-product-1">
            <h4>{product1['title']}</h4>
            {desc1}
        </div>
        <hr>
        <div class="combo-product-2">
            <h4>{product2['title']}</h4>
            {desc2}
        </div>
    </div>
    '''
    
    # Update product
    update_mutation = '''
    mutation updateProduct($input: ProductInput!) {
        productUpdate(input: $input) {
            product {
                id
                variants(first: 1) {
                    edges {
                        node {
                            id
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
    '''
    
    update_input = {
        "id": new_product['id'],
        "descriptionHtml": combo_description,
        "tags": combo_tags,
        "productType": "Combos"
    }
    
    result = client.execute_graphql(update_mutation, {"input": update_input})
    if result and result.get('data', {}).get('productUpdate', {}).get('userErrors'):
        print(f"Warning: Error updating product: {result['data']['productUpdate']['userErrors']}")
    
    # Get the variant ID for pricing update
    if result and 'data' in result and result['data'].get('productUpdate'):
        variant_id = result['data']['productUpdate']['product']['variants']['edges'][0]['node']['id']
        
        # Update variant pricing and SKU using productVariantsBulkUpdate
        variant_mutation = '''
        mutation updateVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
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
        
        variant_input = {
            "id": variant_id,
            "price": str(combo_price),
            "compareAtPrice": str(total_price),
            "inventoryPolicy": "CONTINUE"  # Allow oversell for combos
        }
        
        if total_cost:
            variant_input["inventoryItem"] = {
                "cost": str(total_cost)
            }
        
        variables = {
            "productId": new_product['id'],
            "variants": [variant_input]
        }
        
        result = client.execute_graphql(variant_mutation, variables)
        if result and result.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors'):
            print(f"Warning: Error updating variant: {result['data']['productVariantsBulkUpdate']['userErrors']}")
        
        # Update SKU separately using inventorySku method
        sku_mutation = '''
        mutation updateSku($inventoryItemId: ID!, $sku: String!) {
            inventoryItemUpdate(id: $inventoryItemId, input: {sku: $sku}) {
                inventoryItem {
                    id
                    sku
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        # First get the inventory item ID
        variant_query = '''
        query getVariantInventory($id: ID!) {
            productVariant(id: $id) {
                inventoryItem {
                    id
                }
            }
        }
        '''
        
        variant_result = client.execute_graphql(variant_query, {"id": variant_id})
        if variant_result and 'data' in variant_result and variant_result['data'].get('productVariant'):
            inventory_item_id = variant_result['data']['productVariant']['inventoryItem']['id']
            
            # Update the SKU
            sku_result = client.execute_graphql(sku_mutation, {
                "inventoryItemId": inventory_item_id,
                "sku": combo_sku
            })
            
            if sku_result and sku_result.get('data', {}).get('inventoryItemUpdate', {}).get('userErrors'):
                print(f"Warning: Error updating SKU: {sku_result['data']['inventoryItemUpdate']['userErrors']}")
    
    # Step 3: Create and upload combo image
    if product1['images']['edges'] and product2['images']['edges']:
        print("Creating combo image...")
        image1_url = product1['images']['edges'][0]['node']['url']
        image2_url = product2['images']['edges'][0]['node']['url']
        print(f"Image 1 URL: {image1_url}")
        print(f"Image 2 URL: {image2_url}")
        
        combo_image = create_combo_image(image1_url, image2_url)
        if combo_image:
            print("Combo image created successfully")
            print("Uploading combo image...")
            upload_combo_image(client, new_product['id'], combo_image)
        else:
            print("Failed to create combo image")
    else:
        print("One or both products have no images")
    
    # Step 4: Add combo metafields
    # Combine buybox content if available
    buybox_content = ""
    for product in [product1, product2]:
        for mf in product.get('metafields', {}).get('edges', []):
            node = mf['node']
            if node['namespace'] == 'content' and node['key'] == 'buy_box':
                if buybox_content:
                    buybox_content += "\n<hr>\n"
                buybox_content += node['value']
    
    if buybox_content:
        metafield_mutation = '''
        mutation setMetafield($input: MetafieldsSetInput!) {
            metafieldsSet(metafields: [$input]) {
                metafields {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        
        mf_input = {
            "ownerId": new_product['id'],
            "namespace": "content",
            "key": "buy_box",
            "value": buybox_content,
            "type": "multi_line_text_field"
        }
        
        client.execute_graphql(metafield_mutation, {"input": mf_input})
    
    # Write to CSV if writer provided (for SkuVault integration)
    if csv_writer:
        csv_writer.writerow([
            combo_sku, "", combo_title, "",
            product1['title'], 1, variant1['sku'], "", ""
        ])
        csv_writer.writerow([
            combo_sku, "", combo_title, "",
            product2['title'], 1, variant2['sku'], "", ""
        ])
    
    print(f"\n✓ Combo created successfully!")
    print(f"  Handle: {new_product['handle']}")
    print(f"  SKU: {combo_sku}")
    print(f"  Status: {'Published' if publish else 'Draft'}")
    
    return new_product

def process_csv(client, csv_file):
    """Process combos from CSV file"""
    try:
        # Output CSV for SkuVault
        output_file = csv_file.replace('.csv', '_skuvault.csv')
        
        with open(csv_file, 'r') as infile, open(output_file, 'w', newline='') as outfile:
            reader = csv.DictReader(infile)
            csv_writer = csv.writer(outfile)
            
            # Write SkuVault header
            csv_writer.writerow([
                "Kit Sku", "Kit Code", "Kit Title", "Disable Quantity Sync",
                "Line Item Name", "Quantity", "Sku/Code", "Combine Option", "Statuses"
            ])
            
            success_count = 0
            error_count = 0
            
            for row in reader:
                print(f"\n{'='*60}")
                print(f"Processing combo: {row.get('product1', '')} + {row.get('product2', '')}")
                
                try:
                    # Extract parameters
                    product1 = row.get('product1', '').strip()
                    product2 = row.get('product2', '').strip()
                    sku_suffix = row.get('sku_suffix', '').strip() or None
                    discount_amount = float(row.get('discount_amount', 0)) if row.get('discount_amount') else None
                    discount_percent = float(row.get('discount_percent', 0)) if row.get('discount_percent') else None
                    publish = row.get('publish', '').lower() in ['true', 'yes', '1']
                    
                    if not product1 or not product2:
                        print("Error: Missing product identifiers")
                        error_count += 1
                        continue
                    
                    # Create combo
                    result = create_combo_listing(
                        client, product1, product2, sku_suffix, 
                        discount_amount, discount_percent, None,
                        publish, csv_writer
                    )
                    
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    print(f"Error processing row: {e}")
                    error_count += 1
            
            print(f"\n{'='*60}")
            print(f"CSV processing complete:")
            print(f"  Successful: {success_count}")
            print(f"  Errors: {error_count}")
            print(f"  SkuVault file: {output_file}")
            
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)

def create_sample_csv():
    """Create a sample CSV template"""
    sample_file = "combo_template.csv"
    
    with open(sample_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['product1', 'product2', 'sku_suffix', 'discount_amount', 'discount_percent', 'publish'])
        writer.writerow(['breville-barista-express', 'eureka-mignon-specialita', 'BE-ES1', '200', '', 'false'])
        writer.writerow(['BES870XL', 'GRIND-01', '', '', '15', 'false'])
        writer.writerow(['7234567890123', '9876543210987', 'CUSTOM', '150', '', 'true'])
    
    print(f"Sample CSV created: {sample_file}")
    print("\nColumns:")
    print("  product1: Product identifier (handle, SKU, barcode, or ID)")
    print("  product2: Product identifier (handle, SKU, barcode, or ID)")
    print("  sku_suffix: Optional custom suffix for combo SKU")
    print("  discount_amount: Fixed discount amount (e.g., 200 for $200 off)")
    print("  discount_percent: Percentage discount (e.g., 15 for 15% off)")
    print("  publish: true/false to publish immediately")

def main():
    parser = argparse.ArgumentParser(description='Create machine+grinder combo products')
    
    # Single combo mode
    parser.add_argument('--product1', help='First product (handle, SKU, barcode, or ID)')
    parser.add_argument('--product2', help='Second product (handle, SKU, barcode, or ID)')
    parser.add_argument('--sku-suffix', help='Custom suffix for combo SKU')
    parser.add_argument('--discount', type=float, help='Fixed discount amount')
    parser.add_argument('--discount-percent', type=float, help='Percentage discount')
    parser.add_argument('--price', type=float, help='Set specific price for combo')
    parser.add_argument('--publish', action='store_true', help='Publish immediately')
    
    # Bulk mode
    parser.add_argument('--from-csv', help='Create multiple combos from CSV file')
    parser.add_argument('--sample', action='store_true', help='Create sample CSV template')
    
    args = parser.parse_args()
    
    # Handle sample creation
    if args.sample:
        create_sample_csv()
        return
    
    # Initialize client
    client = ShopifyClient()
    
    # Handle CSV mode
    if args.from_csv:
        if not os.path.exists(args.from_csv):
            print(f"Error: CSV file not found: {args.from_csv}")
            sys.exit(1)
        process_csv(client, args.from_csv)
        return
    
    # Handle single combo mode
    if not args.product1 or not args.product2:
        print("Error: Both --product1 and --product2 are required for single combo creation")
        print("\nUse --help for usage examples")
        sys.exit(1)
    
    if args.discount and args.discount_percent:
        print("Error: Cannot use both --discount and --discount-percent")
        sys.exit(1)
    
    # Create single combo
    create_combo_listing(
        client,
        args.product1, 
        args.product2,
        args.sku_suffix,
        args.discount,
        args.discount_percent,
        args.price,
        args.publish
    )

if __name__ == '__main__':
    main()