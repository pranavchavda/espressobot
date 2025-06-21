#!/usr/bin/env python3
"""
Add images to a product from URLs or local files.

This tool allows adding one or more images to an existing product by providing 
either image URLs or local file paths. Images can be added from any publicly 
accessible URL or from files on your local system.
"""

import os
import sys
import json
import argparse
import requests
import mimetypes
from typing import List, Dict, Optional, Any, Tuple
from base import ShopifyClient

def create_staged_upload(client: ShopifyClient, filename: str, file_size: int, mime_type: str) -> Dict[str, Any]:
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

def upload_to_staged_target(target: Dict[str, Any], file_content: bytes, filename: str) -> None:
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


def process_local_file(client: ShopifyClient, file_path: str, alt_text: Optional[str] = None) -> str:
    """Process a local file and upload it to Shopify."""
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file info
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    mime_type, _ = mimetypes.guess_type(file_path)
    
    if not mime_type or not mime_type.startswith('image/'):
        mime_type = 'image/jpeg'  # Default to JPEG if unknown
    
    # Read file content
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    print(f"  Uploading local file: {filename} ({file_size} bytes, {mime_type})")
    
    # Create staged upload
    target = create_staged_upload(client, filename, file_size, mime_type)
    print(f"  Created staged upload target")
    
    # Upload to staged target
    upload_to_staged_target(target, file_content, filename)
    print(f"  Uploaded to staging")
    
    # Return the resource URL for use with productCreateMedia
    return target['resourceUrl']

def add_product_images(client: ShopifyClient, product_id: str, image_sources: List[str], 
                      alt_texts: Optional[List[str]] = None) -> Dict[str, Any]:
    """Add images to a product from URLs."""
    mutation = """
    mutation createProductMedia($media: [CreateMediaInput!]!, $productId: ID!) {
        productCreateMedia(media: $media, productId: $productId) {
            media {
                ... on MediaImage {
                    id
                    image {
                        url
                        altText
                    }
                    status
                }
            }
            mediaUserErrors {
                field
                message
                code
            }
            product {
                id
                title
                media(first: 10) {
                    edges {
                        node {
                            ... on MediaImage {
                                id
                                image {
                                    url
                                    altText
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    """
    
    # Build media input for URLs
    media = []
    for i, url in enumerate(image_sources):
        media_item = {
            "originalSource": url,
            "mediaContentType": "IMAGE"
        }
        
        # Add alt text if provided
        if alt_texts and i < len(alt_texts) and alt_texts[i]:
            media_item["alt"] = alt_texts[i]
        
        media.append(media_item)
    
    variables = {
        "productId": product_id,
        "media": media
    }
    
    return client.execute_graphql(mutation, variables)

def reorder_images(client: ShopifyClient, product_id: str, media_ids: List[str]) -> Dict[str, Any]:
    """Reorder product images."""
    mutation = """
    mutation reorderProductMedia($id: ID!, $moves: [MoveInput!]!) {
        productReorderMedia(id: $id, moves: $moves) {
            job {
                id
                done
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    # Build moves array
    moves = []
    for i, media_id in enumerate(media_ids):
        moves.append({
            "id": media_id,
            "newPosition": str(i)
        })
    
    variables = {
        "id": product_id,
        "moves": moves
    }
    
    return client.execute_graphql(mutation, variables)

def get_product_images(client: ShopifyClient, product_id: str) -> List[Dict[str, Any]]:
    """Get current product images."""
    query = """
    query getProductImages($id: ID!) {
        product(id: $id) {
            id
            title
            media(first: 50) {
                edges {
                    node {
                        ... on MediaImage {
                            id
                            image {
                                url
                                altText
                            }
                            status
                        }
                    }
                }
            }
        }
    }
    """
    
    variables = {"id": product_id}
    result = client.execute_graphql(query, variables)
    
    if not result.get('data', {}).get('product'):
        return []
    
    media_edges = result['data']['product'].get('media', {}).get('edges', [])
    images = []
    
    for edge in media_edges:
        node = edge.get('node', {})
        if node and 'image' in node:  # It's a MediaImage
            images.append(node)
    
    return images

def delete_product_image(client: ShopifyClient, product_id: str, media_ids: List[str]) -> Dict[str, Any]:
    """Delete product images."""
    mutation = """
    mutation deleteProductMedia($mediaIds: [ID!]!, $productId: ID!) {
        productDeleteMedia(mediaIds: $mediaIds, productId: $productId) {
            deletedMediaIds
            product {
                id
                title
            }
            mediaUserErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {
        "productId": product_id,
        "mediaIds": media_ids
    }
    
    return client.execute_graphql(mutation, variables)

def is_local_file(path: str) -> bool:
    """Check if a path is a local file or URL."""
    return not (path.startswith('http://') or path.startswith('https://'))

def main():
    parser = argparse.ArgumentParser(
        description="Add images to a product from URLs or local files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a single image from URL
  %(prog)s --product "7779055304738" --add "https://example.com/image1.jpg"
  
  # Add multiple images from URLs
  %(prog)s --product "profitec-pro-600" --add "https://example.com/image1.jpg" "https://example.com/image2.jpg"
  
  # Add local images
  %(prog)s --product "BES870XL" --add "/path/to/image1.jpg" "/path/to/image2.png" --local
  
  # Mix local and URL images (use --local and provide full paths for local files)
  %(prog)s --product "7779055304738" --add "/home/user/product.jpg" --local
  
  # Add images with alt text
  %(prog)s --product "BES870XL" --add "image1.jpg" "image2.jpg" --alt "Front view" "Side view" --local
  
  # List current images
  %(prog)s --product "7779055304738" --list
  
  # Delete images by position
  %(prog)s --product "profitec-pro-600" --delete 2,3
  
  # Reorder images
  %(prog)s --product "BES870XL" --reorder 3,1,2,4
  
  # Clear all images
  %(prog)s --product "7779055304738" --clear
        """
    )
    
    parser.add_argument('--product', '-p', required=True,
                        help='Product identifier (ID, handle, SKU, or title)')
    
    # Actions
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('--add', '-a', nargs='+', metavar='SOURCE',
                              help='Add one or more images from URLs or local files')
    action_group.add_argument('--list', '-l', action='store_true',
                              help='List current product images')
    action_group.add_argument('--delete', '-d', 
                              help='Delete images by position (comma-separated, e.g., 1,3)')
    action_group.add_argument('--reorder', '-r',
                              help='Reorder images (comma-separated positions, e.g., 3,1,2)')
    action_group.add_argument('--clear', '-c', action='store_true',
                              help='Remove all images')
    
    # Optional parameters
    parser.add_argument('--alt', nargs='+', metavar='TEXT',
                        help='Alt text for images (one per image)')
    parser.add_argument('--local', action='store_true',
                        help='Treat paths as local files instead of URLs')
    
    args = parser.parse_args()
    
    # Initialize client
    client = ShopifyClient()
    
    # Find product
    print(f"Finding product: {args.product}")
    product_id = client.resolve_product_id(args.product)
    if not product_id:
        print(f"Error: Product not found: {args.product}")
        sys.exit(1)
    
    # Default to list if no action specified
    if not any([args.add, args.delete, args.reorder, args.clear]):
        args.list = True
    
    # Handle actions
    if args.list:
        images = get_product_images(client, product_id)
        if not images:
            print("No images found for this product.")
        else:
            print(f"\nProduct has {len(images)} image(s):")
            print("-" * 60)
            for i, img in enumerate(images, 1):
                image_data = img.get('image') if img else None
                if image_data:
                    url = image_data.get('url', 'N/A')
                    alt = image_data.get('altText', '(no alt text)')
                else:
                    url = 'N/A'
                    alt = '(no alt text)'
                status = img.get('status', 'UNKNOWN') if img else 'UNKNOWN'
                print(f"{i}. {url}")
                print(f"   Alt: {alt}")
                print(f"   Status: {status}")
                print(f"   ID: {img.get('id', 'N/A') if img else 'N/A'}")
                print()
    
    elif args.add:
        # Auto-detect if sources are local files
        if args.local or any(is_local_file(src) and os.path.exists(src) for src in args.add):
            print(f"Processing {len(args.add)} file(s)...")
            
            # Build list of resource URLs and alt texts
            resource_urls = []
            alt_texts_for_upload = []
            
            for i, source in enumerate(args.add):
                alt_text = args.alt[i] if args.alt and i < len(args.alt) else None
                
                if is_local_file(source) and os.path.exists(source):
                    try:
                        print(f"\nProcessing file {i+1}/{len(args.add)}: {source}")
                        resource_url = process_local_file(client, source, alt_text)
                        resource_urls.append(resource_url)
                        alt_texts_for_upload.append(alt_text)
                    except Exception as e:
                        print(f"  Error: {e}")
                else:
                    print(f"\nSkipping URL or non-existent file: {source}")
            
            if resource_urls:
                # Use productCreateMedia with resource URLs
                print(f"\nAdding {len(resource_urls)} image(s) to product...")
                result = add_product_images(client, product_id, resource_urls, alt_texts_for_upload)
                
                # Check for errors
                if result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors'):
                    errors = result['data']['productCreateMedia']['mediaUserErrors']
                    print(f"Error adding images: {errors}")
                else:
                    media = result.get('data', {}).get('productCreateMedia', {}).get('media', [])
                    print(f"\n✅ Successfully added {len(media)} image(s)")
                    
                    # Show total images
                    product = result.get('data', {}).get('productCreateMedia', {}).get('product', {})
                    if product:
                        total_media = len(product.get('media', {}).get('edges', []))
                        print(f"Product now has {total_media} total image(s)")
            
        else:
            # URL-based upload (original functionality)
            print(f"Adding {len(args.add)} image(s) from URLs...")
            
            result = add_product_images(client, product_id, args.add, args.alt)
            
            # Check for errors
            if result.get('data', {}).get('productCreateMedia', {}).get('mediaUserErrors'):
                errors = result['data']['productCreateMedia']['mediaUserErrors']
                print(f"Error adding images: {errors}")
                sys.exit(1)
            
            media = result.get('data', {}).get('productCreateMedia', {}).get('media', [])
            if media:
                print(f"✅ Successfully added {len(media)} image(s)")
                for m in media:
                    if m and 'image' in m and m['image']:
                        print(f"   - {m['image'].get('url', 'Processing...')}")
                        if m.get('status') != 'READY':
                            print(f"     Status: {m.get('status', 'PROCESSING')}")
                    elif m:
                        print(f"   - Image processing... (Status: {m.get('status', 'PROCESSING')})")
            
            # Show total images
            product = result.get('data', {}).get('productCreateMedia', {}).get('product', {})
            if product:
                total_media = len(product.get('media', {}).get('edges', []))
                print(f"\nProduct now has {total_media} total image(s)")
    
    elif args.delete:
        # Get current images
        images = get_product_images(client, product_id)
        if not images:
            print("No images to delete.")
            sys.exit(0)
        
        # Parse positions
        try:
            positions = [int(p.strip()) - 1 for p in args.delete.split(',')]
        except ValueError:
            print("Error: Invalid position format. Use comma-separated numbers (e.g., 1,3)")
            sys.exit(1)
        
        # Validate positions
        media_ids = []
        for pos in positions:
            if 0 <= pos < len(images):
                media_ids.append(images[pos]['id'])
            else:
                print(f"Warning: Position {pos + 1} out of range (1-{len(images)})")
        
        if not media_ids:
            print("No valid images to delete.")
            sys.exit(0)
        
        print(f"Deleting {len(media_ids)} image(s)...")
        result = delete_product_image(client, product_id, media_ids)
        
        if result.get('data', {}).get('productDeleteMedia', {}).get('mediaUserErrors'):
            errors = result['data']['productDeleteMedia']['mediaUserErrors']
            print(f"Error deleting images: {errors}")
            sys.exit(1)
        
        deleted = result.get('data', {}).get('productDeleteMedia', {}).get('deletedMediaIds', [])
        print(f"✅ Successfully deleted {len(deleted)} image(s)")
    
    elif args.reorder:
        # Get current images
        images = get_product_images(client, product_id)
        if not images:
            print("No images to reorder.")
            sys.exit(0)
        
        # Parse positions
        try:
            positions = [int(p.strip()) - 1 for p in args.reorder.split(',')]
        except ValueError:
            print("Error: Invalid position format. Use comma-separated numbers (e.g., 3,1,2)")
            sys.exit(1)
        
        # Validate positions
        if len(positions) != len(images):
            print(f"Error: Must specify all {len(images)} positions")
            sys.exit(1)
        
        if sorted(positions) != list(range(len(images))):
            print("Error: Invalid positions. Each position must be used exactly once")
            sys.exit(1)
        
        # Build new order
        reordered_ids = [images[i]['id'] for i in positions]
        
        print("Reordering images...")
        result = reorder_images(client, product_id, reordered_ids)
        
        if result.get('data', {}).get('productReorderMedia', {}).get('userErrors'):
            errors = result['data']['productReorderMedia']['userErrors']
            print(f"Error reordering images: {errors}")
            sys.exit(1)
        
        print("✅ Successfully reordered images")
        
        # Show new order
        images = get_product_images(client, product_id)
        print("\nNew image order:")
        for i, img in enumerate(images, 1):
            url = img.get('image', {}).get('url', 'N/A')
            print(f"{i}. {url}")
    
    elif args.clear:
        # Get all current images
        images = get_product_images(client, product_id)
        if not images:
            print("No images to clear.")
            sys.exit(0)
        
        media_ids = [img['id'] for img in images]
        
        print(f"Clearing {len(media_ids)} image(s)...")
        result = delete_product_image(client, product_id, media_ids)
        
        if result.get('data', {}).get('productDeleteMedia', {}).get('mediaUserErrors'):
            errors = result['data']['productDeleteMedia']['mediaUserErrors']
            print(f"Error clearing images: {errors}")
            sys.exit(1)
        
        print("✅ Successfully cleared all images")

if __name__ == "__main__":
    main()