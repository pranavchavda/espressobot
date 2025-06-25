#!/usr/bin/env python3
"""
Tool to manage product features box using Shopify metaobjects.
Provides easy add, update, remove, and reorder operations for product features.
"""

import os
import sys
import json
import argparse
import requests
from typing import List, Dict, Optional, Tuple

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

def get_metaobject_definition() -> Optional[str]:
    """Get the metaobject definition ID for product_features_block."""
    query = '''
    {
        metaobjectDefinitions(first: 100) {
            edges {
                node {
                    id
                    type
                }
            }
        }
    }
    '''
    
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    data = response.json()
    
    if 'errors' in data:
        print(f"GraphQL Error: {data['errors']}")
        return None
    
    edges = data.get('data', {}).get('metaobjectDefinitions', {}).get('edges', [])
    for edge in edges:
        if edge['node']['type'] == 'product_features_block':
            return edge['node']['id']
    
    return None

def get_current_features(product_id: str) -> Tuple[List[Dict], Optional[str]]:
    """Get current features from metafield. Returns (features, metafield_id)."""
    query = f'''{{
        product(id: "{product_id}") {{
            featuresMetafield: metafield(namespace: "content", key: "features_box") {{
                id
                value
                references(first: 50) {{
                    edges {{
                        node {{
                            __typename
                            ... on Metaobject {{
                                id
                                type
                                fields {{
                                    key
                                    value
                                    type
                                }}
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}'''
    
    response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
    data = response.json()
    
    if 'errors' in data:
        print(f"GraphQL Error: {data['errors']}")
        return [], None
    
    metafield = data.get('data', {}).get('product', {}).get('featuresMetafield')
    if not metafield:
        return [], None
    
    features = []
    for edge in metafield.get('references', {}).get('edges', []):
        node = edge['node']
        if node['__typename'] == 'Metaobject':
            feature = {'id': node['id'], 'fields': {}}
            for field in node['fields']:
                feature['fields'][field['key']] = {
                    'value': field['value'],
                    'type': field['type']
                }
            features.append(feature)
    
    return features, metafield.get('id')

def create_feature_metaobject(text: str, image_id: Optional[str] = None) -> Optional[str]:
    """Create a new feature metaobject."""
    definition_id = get_metaobject_definition()
    if not definition_id:
        print("Error: Could not find product_features_block metaobject definition")
        return None
    
    fields = [
        {
            "key": "text",
            "value": text
        }
    ]
    
    if image_id:
        fields.append({
            "key": "image",
            "value": image_id
        })
    
    mutation = """
    mutation createMetaobject($metaobject: MetaobjectCreateInput!) {
        metaobjectCreate(metaobject: $metaobject) {
            metaobject {
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
        "metaobject": {
            "type": "product_features_block",
            "fields": fields
        }
    }
    
    response = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    result = response.json()
    
    if 'errors' in result:
        print(f"GraphQL Errors: {result['errors']}")
        return None
    
    user_errors = result.get('data', {}).get('metaobjectCreate', {}).get('userErrors', [])
    if user_errors:
        print(f"User Errors: {user_errors}")
        return None
    
    metaobject = result.get('data', {}).get('metaobjectCreate', {}).get('metaobject')
    return metaobject['id'] if metaobject else None

def update_feature_metaobject(metaobject_id: str, text: str, image_id: Optional[str] = None) -> bool:
    """Update an existing feature metaobject."""
    fields = [
        {
            "key": "text",
            "value": text
        }
    ]
    
    if image_id:
        fields.append({
            "key": "image",
            "value": image_id
        })
    
    mutation = """
    mutation updateMetaobject($id: ID!, $metaobject: MetaobjectUpdateInput!) {
        metaobjectUpdate(id: $id, metaobject: $metaobject) {
            metaobject {
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
        "id": metaobject_id,
        "metaobject": {
            "fields": fields
        }
    }
    
    response = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    result = response.json()
    
    if 'errors' in result:
        print(f"GraphQL Errors: {result['errors']}")
        return False
    
    user_errors = result.get('data', {}).get('metaobjectUpdate', {}).get('userErrors', [])
    if user_errors:
        print(f"User Errors: {user_errors}")
        return False
    
    return True

def delete_feature_metaobject(metaobject_id: str) -> bool:
    """Delete a feature metaobject."""
    mutation = """
    mutation deleteMetaobject($id: ID!) {
        metaobjectDelete(id: $id) {
            deletedId
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {"id": metaobject_id}
    
    response = requests.post(GRAPHQL_URL, json={"query": mutation, "variables": variables}, headers=HEADERS)
    result = response.json()
    
    if 'errors' in result:
        print(f"GraphQL Errors: {result['errors']}")
        return False
    
    user_errors = result.get('data', {}).get('metaobjectDelete', {}).get('userErrors', [])
    if user_errors:
        print(f"User Errors: {user_errors}")
        return False
    
    return True

def update_features_metafield(product_id: str, metaobject_ids: List[str], metafield_id: Optional[str] = None) -> bool:
    """Update or create the features_box metafield with metaobject references."""
    # Always use the same mutation - metafieldsSet handles both create and update
    mutation = """
    mutation setMetafield($input: [MetafieldsSetInput!]!) {
        metafieldsSet(metafields: $input) {
            metafields {
                id
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    # Always provide full metafield definition - metafieldsSet will update if exists, create if not
    variables = {
        "input": [{
            "ownerId": product_id,
            "namespace": "content",
            "key": "features_box",
            "type": "list.mixed_reference",
            "value": json.dumps(metaobject_ids)
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
        text = feature['fields'].get('text', {}).get('value', '')
        image_id = feature['fields'].get('image', {}).get('value')
        
        # Split on first newline to separate title from description
        lines = text.split('\n', 1)
        if numbered:
            print(f"{i}. {lines[0]}")
        else:
            print(f"   {lines[0]}")
        if len(lines) > 1:
            print(f"   {lines[1].strip()}")
        if image_id:
            print(f"   [Image: {image_id}]")
        print()

def parse_feature_text(title: str, description: Optional[str] = None) -> str:
    """Parse feature input into the correct format."""
    if description:
        return f"**{title}**  \n{description}"
    else:
        # Check if title already has ** formatting
        if '**' in title and '\n' in title:
            return title
        else:
            return f"**{title}**"

def main():
    parser = argparse.ArgumentParser(
        description='Manage product features box using metaobjects',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List current features
  %(prog)s --product "profitec-move" --list
  
  # Add a new feature (text only)
  %(prog)s --product "PRO-MOVE-B" --add "E61 Group Head" "Commercial-grade group provides temperature stability"
  
  # Add a feature with image
  %(prog)s --product "7779055304738" --add "E61 Group Head" "Temperature stability" --image "gid://shopify/MediaImage/123"
  
  # Update an existing feature (by position)
  %(prog)s --product "product-handle" --update 2 "Updated Feature" "New description"
  
  # Remove a feature (by position)
  %(prog)s --product "gid://shopify/Product/123" --remove 3
  
  # Reorder features
  %(prog)s --product "SKU123" --reorder 3,1,2,4,5
  
  # Clear all features
  %(prog)s --product "product-handle" --clear
  
  # Migrate from JSON to metaobjects
  %(prog)s --product "product-handle" --migrate-from-json
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
    action_group.add_argument('--clear', '-c', action='store_true',
                              help='Clear all features')
    action_group.add_argument('--migrate-from-json', action='store_true',
                              help='Migrate features from JSON metafield to metaobjects')
    
    # Optional image parameter
    parser.add_argument('--image', '-i',
                        help='Image ID for add/update operations (e.g., gid://shopify/MediaImage/123)')
    
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
    current_features, metafield_id = get_current_features(product_id)
    
    # Default action is list if no action specified
    if not any([args.add, args.update, args.remove, args.reorder, args.clear, args.migrate_from_json]):
        args.list = True
    
    # Handle actions
    if args.list:
        display_features(current_features)
        
    elif args.add:
        if len(args.add) == 1:
            # Single argument - might be formatted already
            text = parse_feature_text(args.add[0])
        elif len(args.add) == 2:
            # Title and description
            text = parse_feature_text(args.add[0], args.add[1])
        else:
            # Join all arguments after first as description
            text = parse_feature_text(args.add[0], ' '.join(args.add[1:]))
        
        # Create new metaobject
        new_metaobject_id = create_feature_metaobject(text, args.image)
        if not new_metaobject_id:
            print("Error: Failed to create feature metaobject")
            sys.exit(1)
        
        # Update metafield with new reference
        metaobject_ids = [f['id'] for f in current_features] + [new_metaobject_id]
        
        if update_features_metafield(product_id, metaobject_ids, metafield_id):
            print(f"\n✓ Added feature: {args.add[0]}")
            current_features.append({
                'id': new_metaobject_id,
                'fields': {
                    'text': {'value': text},
                    'image': {'value': args.image} if args.image else {}
                }
            })
            display_features(current_features)
        else:
            print("Error: Failed to update features metafield")
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
                text = parse_feature_text(args.update[1])
            elif len(args.update) == 3:
                # Position, title, and description
                text = parse_feature_text(args.update[1], args.update[2])
            else:
                # Join all arguments after position and title as description
                text = parse_feature_text(args.update[1], ' '.join(args.update[2:]))
            
            # Update the metaobject
            metaobject_id = current_features[position]['id']
            if update_feature_metaobject(metaobject_id, text, args.image):
                print(f"\n✓ Updated feature at position {position + 1}")
                current_features[position]['fields']['text']['value'] = text
                if args.image:
                    current_features[position]['fields']['image'] = {'value': args.image}
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
        
        # Delete the metaobject
        metaobject_id = current_features[position]['id']
        if not delete_feature_metaobject(metaobject_id):
            print("Error: Failed to delete feature metaobject")
            sys.exit(1)
        
        # Remove from list and update metafield
        current_features.pop(position)
        metaobject_ids = [f['id'] for f in current_features]
        
        if update_features_metafield(product_id, metaobject_ids, metafield_id):
            print(f"\n✓ Removed feature at position {args.remove}")
            display_features(current_features)
        else:
            print("Error: Failed to update features metafield")
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
            reordered_ids = [current_features[i]['id'] for i in positions]
            
            if update_features_metafield(product_id, reordered_ids, metafield_id):
                print("\n✓ Features reordered")
                reordered_features = [current_features[i] for i in positions]
                display_features(reordered_features)
            else:
                print("Error: Failed to reorder features")
                sys.exit(1)
                
        except (ValueError, IndexError):
            print("Error: Invalid reorder format. Use comma-separated positions (e.g., 3,1,2)")
            sys.exit(1)
            
    elif args.clear:
        # Delete all metaobjects
        for feature in current_features:
            if not delete_feature_metaobject(feature['id']):
                print(f"Warning: Failed to delete metaobject {feature['id']}")
        
        # Clear the metafield
        if metafield_id and update_features_metafield(product_id, [], metafield_id):
            print("\n✓ All features cleared")
        else:
            print("Error: Failed to clear features metafield")
            sys.exit(1)
            
    elif args.migrate_from_json:
        # Get JSON features
        query = f'''{{
            product(id: "{product_id}") {{
                jsonMetafield: metafield(namespace: "content", key: "featuresjson") {{
                    value
                }}
            }}
        }}'''
        
        response = requests.post(GRAPHQL_URL, json={"query": query}, headers=HEADERS)
        data = response.json()
        
        json_metafield = data.get('data', {}).get('product', {}).get('jsonMetafield')
        if not json_metafield:
            print("No JSON features found to migrate")
            sys.exit(0)
        
        try:
            features_data = json.loads(json_metafield['value'])
            json_features = features_data.get('features', [])
        except json.JSONDecodeError:
            print("Error: Could not parse JSON features")
            sys.exit(1)
        
        if not json_features:
            print("No features to migrate")
            sys.exit(0)
        
        print(f"\nFound {len(json_features)} features to migrate")
        
        # Create metaobjects for each feature
        new_metaobject_ids = []
        for i, feature in enumerate(json_features):
            copy = feature.get('copy', '')
            print(f"Migrating feature {i+1}/{len(json_features)}...")
            
            metaobject_id = create_feature_metaobject(copy)
            if metaobject_id:
                new_metaobject_ids.append(metaobject_id)
            else:
                print(f"Warning: Failed to create metaobject for feature {i+1}")
        
        if new_metaobject_ids:
            # Update the features_box metafield
            if update_features_metafield(product_id, new_metaobject_ids, metafield_id):
                print(f"\n✓ Successfully migrated {len(new_metaobject_ids)} features to metaobjects")
                
                # Optional: Delete the old JSON metafield
                print("\nNote: The old featuresjson metafield is still present. Remove it manually if desired.")
            else:
                print("Error: Failed to update features_box metafield")
                # Clean up created metaobjects
                for mid in new_metaobject_ids:
                    delete_feature_metaobject(mid)
                sys.exit(1)
        else:
            print("Error: No features were successfully migrated")
            sys.exit(1)

if __name__ == '__main__':
    main()