#!/usr/bin/env python3
"""Add or remove tags from products."""

import sys
import argparse
from base import ShopifyClient, parse_tags, print_json


def manage_tags(action: str, identifier: str, tags: list):
    """Add or remove tags from a product."""
    client = ShopifyClient()
    
    # Resolve product ID
    product_id = client.resolve_product_id(identifier)
    if not product_id:
        print(f"Error: Product not found with identifier: {identifier}", file=sys.stderr)
        sys.exit(1)
    
    # Choose mutation based on action
    if action == 'add':
        mutation = '''
        mutation addTags($id: ID!, $tags: [String!]!) {
            tagsAdd(id: $id, tags: $tags) {
                node {
                    ... on Product {
                        id
                        title
                        tags
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        operation = 'tagsAdd'
    else:  # remove
        mutation = '''
        mutation removeTags($id: ID!, $tags: [String!]!) {
            tagsRemove(id: $id, tags: $tags) {
                node {
                    ... on Product {
                        id
                        title
                        tags
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        '''
        operation = 'tagsRemove'
    
    variables = {
        'id': product_id,
        'tags': tags
    }
    
    result = client.execute_graphql(mutation, variables)
    
    # Check for errors
    if not client.check_user_errors(result, operation):
        sys.exit(1)
    
    return result.get('data', {}).get(operation)


def main():
    parser = argparse.ArgumentParser(
        description='Add or remove tags from products',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Add tags
  python manage_tags.py --action add --product "1234567890" --tags "sale,featured"
  python manage_tags.py -a add -p "delonghi-dedica" -t "espresso-machines,consumer"
  
  # Remove tags
  python manage_tags.py --action remove --product "EC685M" --tags "clearance"
  python manage_tags.py -a remove -p "1234567890" -t "old-tag,unused-tag"
  
  # List current tags
  python manage_tags.py --product "1234567890" --list
        '''
    )
    
    parser.add_argument('--action', '-a', choices=['add', 'remove'],
                       help='Action to perform')
    parser.add_argument('--product', '-p', required=True,
                       help='Product ID, handle, SKU, or title')
    parser.add_argument('--tags', '-t',
                       help='Comma-separated list of tags')
    parser.add_argument('--list', '-l', action='store_true',
                       help='List current tags only')
    
    args = parser.parse_args()
    
    # Handle list mode
    if args.list:
        client = ShopifyClient()
        product_id = client.resolve_product_id(args.product)
        if not product_id:
            print(f"Error: Product not found with identifier: {args.product}", file=sys.stderr)
            sys.exit(1)
        
        query = '''
        query getProductTags($id: ID!) {
            product(id: $id) {
                id
                title
                tags
            }
        }
        '''
        
        result = client.execute_graphql(query, {'id': product_id})
        product = result.get('data', {}).get('product')
        
        if product:
            print(f"Product: {product['title']}")
            print(f"Tags ({len(product['tags'])}): {', '.join(product['tags'])}")
        sys.exit(0)
    
    # Validate arguments for add/remove
    if not args.action or not args.tags:
        print("Error: --action and --tags are required", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    # Parse tags
    tags = parse_tags(args.tags)
    if not tags:
        print("Error: No valid tags provided", file=sys.stderr)
        sys.exit(1)
    
    # Perform action
    result = manage_tags(args.action, args.product, tags)
    
    # Display results
    if result and result.get('node'):
        product = result['node']
        action_word = "added to" if args.action == 'add' else "removed from"
        print(f"✅ Successfully {action_word} product")
        print(f"Product: {product['title']}")
        print(f"Tags {action_word}: {', '.join(tags)}")
        print(f"Current tags ({len(product['tags'])}): {', '.join(product['tags'])}")
    else:
        print("No changes made", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()