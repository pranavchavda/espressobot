#!/usr/bin/env python3
"""Execute GraphQL queries on Shopify Admin API."""

import sys
import argparse
import json
from base import ShopifyClient, print_json


def main():
    parser = argparse.ArgumentParser(
        description='Execute GraphQL queries on Shopify Admin API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Simple query
  python graphql_query.py '{ shop { name } }'
  
  # Query with variables
  python graphql_query.py 'query getProduct($id: ID!) { product(id: $id) { title } }' --variables '{"id": "gid://shopify/Product/123"}'
  
  # From file
  python graphql_query.py --file query.graphql
        '''
    )
    
    parser.add_argument('query', nargs='?', help='GraphQL query string')
    parser.add_argument('--file', '-f', help='Read query from file')
    parser.add_argument('--variables', '-v', help='Query variables as JSON string')
    parser.add_argument('--output', '-o', choices=['json', 'pretty', 'raw'], 
                       default='pretty', help='Output format (default: pretty)')
    
    args = parser.parse_args()
    
    # Get query from argument or file
    if args.file:
        try:
            with open(args.file, 'r') as f:
                query = f.read()
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.query:
        query = args.query
    else:
        print("Error: Provide query as argument or use --file", file=sys.stderr)
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
    
    # Execute query
    client = ShopifyClient()
    result = client.execute_graphql(query, variables)
    
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