#!/usr/bin/env python3
"""Execute GraphQL mutations on Shopify Admin API."""

import sys
import argparse
import json
from base import ShopifyClient, print_json


def main():
    parser = argparse.ArgumentParser(
        description='Execute GraphQL mutations on Shopify Admin API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Add tags to product
  python graphql_mutation.py 'mutation addTags($id: ID!, $tags: [String!]!) { tagsAdd(id: $id, tags: $tags) { node { ... on Product { id tags } } userErrors { field message } } }' --variables '{"id": "gid://shopify/Product/123", "tags": ["sale"]}'
  
  # Update product
  python graphql_mutation.py --file update_product.graphql --variables '{"input": {"id": "gid://shopify/Product/123", "title": "New Title"}}'
        '''
    )
    
    parser.add_argument('mutation', nargs='?', help='GraphQL mutation string')
    parser.add_argument('--file', '-f', help='Read mutation from file')
    parser.add_argument('--variables', '-v', help='Mutation variables as JSON string')
    parser.add_argument('--output', '-o', choices=['json', 'pretty', 'raw'], 
                       default='pretty', help='Output format (default: pretty)')
    
    args = parser.parse_args()
    
    # Get mutation from argument or file
    if args.file:
        try:
            with open(args.file, 'r') as f:
                mutation = f.read()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.mutation:
        mutation = args.mutation
    else:
        print("Error: Provide mutation as argument or use --file", file=sys.stderr)
        parser.print_help()
        sys.exit(1)
    
    # Parse variables if provided
    variables = None
    if args.variables:
        try:
            variables = json.loads(args.variables)
        except json.JSONDecodeError as e:
            print(f"Error parsing variables JSON: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Execute mutation
    client = ShopifyClient()
    result = client.execute_graphql(mutation, variables)
    
    # Check for user errors
    if not client.check_user_errors(result, 'mutation'):
        sys.exit(1)
    
    # Output results
    if args.output == 'raw':
        print(json.dumps(result))
    elif args.output == 'json':
        print_json(result['data'] if 'data' in result else result)
    else:  # pretty
        if 'data' in result:
            print_json(result['data'])
        else:
            print_json(result)


if __name__ == '__main__':
    main()