#!/usr/bin/env python3
"""
Tool to manage product features box metafield on Shopify.
Provides easy add, update, remove, and reorder operations for product features.
"""

import os
import sys
import json
import argparse
import requests
from typing import List, Dict, Optional

# Get Shopify credentials from environment
SHOPIFY_SHOP_URL = os.environ.get('SHOPIFY_SHOP_URL')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')

if not SHOPIFY_SHOP_URL or not SHOPIFY_ACCESS_TOKEN:
    print("Error: Missing SHOPIFY_SHOP_URL or SHOPIFY_ACCESS_TOKEN environment variables")
    sys.exit(1)

# GraphQL endpoint
GRAPHQL_URL = f"{SHOPIFY_SHOP_URL}/admin/api/2024-10/graphql.json"
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json"
}

def find_product(identifier: str) -> Optional[Dict]:
    """Find product by ID, handle, SKU, or title."""
    # Check if it's a GID
    if identifier.startswith('gid://'):
        query = f'{{ product(id: "{identifier}") {{ id title handle }} }}'
    elif identifier.isdigit():
        query = f'{{ product(id: "gid://shopify/Product/{identifier}") {{ id title handle }} }}'
    else:
        # Search by handle, SKU, or title
        query = f'''{{
            products(first: 10, query: "handle:{identifier} OR sku:{identifier} OR title:{identifier}") {{
                edges {{
                    node {{
                        id
                        title
                        handle
                    }}
                }}
            }}
        }}'''
    
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    data = response.json()
    
    if 'errors' in data:
        print(f"GraphQL Error: {data['errors']}")
        return None
    
    if identifier.startswith('gid://') or identifier.isdigit():
        product = data.get('data', {}).get('product')
        if product:
            return product
    else:
        edges = data.get('data', {}).get('products', {}).get('edges', [])
        if edges:
            return edges[0]['node']
    
    return None

def get_current_features(product_id: str) -> List[Dict]:
    """Get current features from metafield."""
    query = f'''{{
        product(id: "{product_id}") {{
            metafield(namespace: "content", key: "featuresjson") {{
                value
            }}
        }}
    }}'''
    
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    data = response.json()
    
    if 'errors' in data:
        print(f"GraphQL Error: {data['errors']}")
        return []
    
    metafield = data.get('data', {}).get('product', {}).get('metafield')
    if metafield and metafield['value']:
        try:
            features_data = json.loads(metafield['value'])
            return features_data.get('features', [])
        except json.JSONDecodeError:
            print("Warning: Could not parse existing features JSON")
    
    return []

def update_features(product_id: str, features: List[Dict]) -> bool:
    """Update features metafield."""
    mutation = """
    mutation updateMetafield($input: [MetafieldsSetInput!]!) {
        metafieldsSet(metafields: $input) {
            metafields {
                id
                namespace
                key
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    features_json = {"features": features}
    
    variables = {
        "input": [{
            "ownerId": product_id,
            "namespace": "content",
            "key": "featuresjson",
            "value": json.dumps(features_json),
            "type": "json"
        }]
    }
    
    response = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    result = response.json()
    
    if 'errors' in result:
        print(f"GraphQL Errors: {result['errors']}")
        return False
    
    user_errors = result.get('data', {}).get('metafieldsSet', {}).get('userErrors', [])
    if user_errors:
        print(f"User Errors: {user_errors}")
        return False
    
    return True

def display_features(features: List[Dict], numbered: bool = True):
    """Display features in a readable format."""
    if not features:
        print("No features found.")
        return
    
    print("\nCurrent Features:")
    print("-" * 50)
    for i, feature in enumerate(features, 1):
        copy = feature.get('copy', '')
        # Split on first newline to separate title from description
        lines = copy.split('\n', 1)
        if numbered:
            print(f"{i}. {lines[0]}")
        else:
            print(f"   {lines[0]}")
        if len(lines) > 1:
            print(f"   {lines[1]}")
        print()

def parse_feature_input(title: str, description: Optional[str] = None) -> Dict:
    """Parse feature input into the correct format."""
    if description:
        copy = f"**{title}**\n{description}"
    else:
        # Check if title already has ** formatting
        if '**' in title and '\n' in title:
            copy = title
        else:
            copy = f"**{title}**"
    
    return {"copy": copy}

def main():
    parser = argparse.ArgumentParser(
        description='Manage product features box metafield',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List current features
  %(prog)s --product "breville-barista-express" --list
  
  # Add a new feature
  %(prog)s --product "BES870XL" --add "15 Bar Pump" "Professional pressure for authentic espresso"
  
  # Update an existing feature (by position)
  %(prog)s --product "7234567890123" --update 2 "Updated Feature" "New description"
  
  # Remove a feature (by position)
  %(prog)s --product "product-handle" --remove 3
  
  # Reorder features
  %(prog)s --product "gid://shopify/Product/123" --reorder 3,1,2,4,5
  
  # Replace all features from JSON file
  %(prog)s --product "SKU123" --replace features.json
  
  # Clear all features
  %(prog)s --product "product-handle" --clear
        """
    )
    
    parser.add_argument('--product', '-p', required=True,
                        help='Product identifier (ID, GID, handle, SKU, or title)')
    
    # Actions
    action_group = parser.add_mutually_exclusive_group()
    action_group.add_argument('--list', '-l', action='store_true',
                              help='List current features')
    action_group.add_argument('--add', '-a', nargs='+',
                              help='Add a new feature (title [description])')
    action_group.add_argument('--update', '-u', nargs='+',
                              help='Update feature at position (position title [description])')
    action_group.add_argument('--remove', '-r', type=int,
                              help='Remove feature at position')
    action_group.add_argument('--reorder', '-o',
                              help='Reorder features (comma-separated positions, e.g., 3,1,2)')
    action_group.add_argument('--replace', '-R', type=str,
                              help='Replace all features from JSON file')
    action_group.add_argument('--clear', '-c', action='store_true',
                              help='Clear all features')
    
    args = parser.parse_args()
    
    # Find product
    print(f"Finding product: {args.product}")
    product = find_product(args.product)
    if not product:
        print(f"Error: Product not found: {args.product}")
        sys.exit(1)
    
    print(f"Found: {product['title']} ({product['handle']})")
    product_id = product['id']
    
    # Get current features
    current_features = get_current_features(product_id)
    
    # Default action is list if no action specified
    if not any([args.add, args.update, args.remove, args.reorder, args.replace, args.clear]):
        args.list = True
    
    # Handle actions
    if args.list:
        display_features(current_features)
        
    elif args.add:
        if len(args.add) == 1:
            # Single argument - might be formatted already
            new_feature = parse_feature_input(args.add[0])
        elif len(args.add) == 2:
            # Title and description
            new_feature = parse_feature_input(args.add[0], args.add[1])
        else:
            # Join all arguments after first as description
            new_feature = parse_feature_input(args.add[0], ' '.join(args.add[1:]))
        
        current_features.append(new_feature)
        
        if update_features(product_id, current_features):
            print(f"\n✓ Added feature: {args.add[0]}")
            display_features(current_features)
        else:
            print("Error: Failed to add feature")
            sys.exit(1)
            
    elif args.update:
        if len(args.update) < 2:
            print("Error: Update requires position and at least a title")
            sys.exit(1)
        
        try:
            position = int(args.update[0]) - 1  # Convert to 0-indexed
            if position < 0 or position >= len(current_features):
                print(f"Error: Invalid position {position + 1}. Must be between 1 and {len(current_features)}")
                sys.exit(1)
            
            if len(args.update) == 2:
                # Position and title only
                updated_feature = parse_feature_input(args.update[1])
            elif len(args.update) == 3:
                # Position, title, and description
                updated_feature = parse_feature_input(args.update[1], args.update[2])
            else:
                # Join all arguments after position and title as description
                updated_feature = parse_feature_input(args.update[1], ' '.join(args.update[2:]))
            
            current_features[position] = updated_feature
            
            if update_features(product_id, current_features):
                print(f"\n✓ Updated feature at position {position + 1}")
                display_features(current_features)
            else:
                print("Error: Failed to update feature")
                sys.exit(1)
                
        except ValueError:
            print("Error: First argument for update must be a position number")
            sys.exit(1)
            
    elif args.remove:
        position = args.remove - 1  # Convert to 0-indexed
        if position < 0 or position >= len(current_features):
            print(f"Error: Invalid position {args.remove}. Must be between 1 and {len(current_features)}")
            sys.exit(1)
        
        removed = current_features.pop(position)
        
        if update_features(product_id, current_features):
            print(f"\n✓ Removed feature at position {args.remove}")
            display_features(current_features)
        else:
            print("Error: Failed to remove feature")
            sys.exit(1)
            
    elif args.reorder:
        try:
            positions = [int(p.strip()) - 1 for p in args.reorder.split(',')]
            
            # Validate positions
            if len(positions) != len(current_features):
                print(f"Error: Must specify all {len(current_features)} positions")
                sys.exit(1)
            
            if sorted(positions) != list(range(len(current_features))):
                print("Error: Invalid positions. Each position must be used exactly once")
                sys.exit(1)
            
            # Reorder features
            new_features = [current_features[i] for i in positions]
            
            if update_features(product_id, new_features):
                print("\n✓ Features reordered")
                display_features(new_features)
            else:
                print("Error: Failed to reorder features")
                sys.exit(1)
                
        except (ValueError, IndexError):
            print("Error: Invalid reorder format. Use comma-separated positions (e.g., 3,1,2)")
            sys.exit(1)
            
    elif args.replace:
        try:
            with open(args.replace, 'r') as f:
                data = json.load(f)
            
            # Support both direct array and object with features key
            if isinstance(data, list):
                new_features = data
            elif isinstance(data, dict) and 'features' in data:
                new_features = data['features']
            else:
                print("Error: JSON must be an array of features or object with 'features' key")
                sys.exit(1)
            
            if update_features(product_id, new_features):
                print(f"\n✓ Replaced all features from {args.replace}")
                display_features(new_features)
            else:
                print("Error: Failed to replace features")
                sys.exit(1)
                
        except FileNotFoundError:
            print(f"Error: File not found: {args.replace}")
            sys.exit(1)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in file: {args.replace}")
            sys.exit(1)
            
    elif args.clear:
        if update_features(product_id, []):
            print("\n✓ All features cleared")
        else:
            print("Error: Failed to clear features")
            sys.exit(1)

if __name__ == '__main__':
    main()