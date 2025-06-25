#!/usr/bin/env python3
"""
Manage URL redirects in Shopify store.

Usage:
    python tools/manage_redirects.py --action create --from "/old-path" --to "/new-path"
    python tools/manage_redirects.py --action list
    python tools/manage_redirects.py --action delete --id "gid://shopify/UrlRedirect/123"
"""

import sys
import argparse
from typing import Dict, Any, Optional
from base import ShopifyClient, print_json


def create_redirect(path: str, target: str) -> Optional[Dict[str, Any]]:
    """Create a URL redirect."""
    client = ShopifyClient()
    
    mutation = """
    mutation createUrlRedirect($redirect: UrlRedirectInput!) {
        urlRedirectCreate(urlRedirect: $redirect) {
            urlRedirect {
                id
                path
                target
            }
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {
        "redirect": {
            "path": path,
            "target": target
        }
    }
    
    result = client.execute_graphql(mutation, variables)
    
    # Check for errors
    if not client.check_user_errors(result, "urlRedirectCreate"):
        return None
    
    data = result.get('data', {}).get('urlRedirectCreate', {})
    if data and 'urlRedirect' in data:
        return data['urlRedirect']
    return None


def list_redirects(limit: int = 50) -> list:
    """List URL redirects."""
    client = ShopifyClient()
    
    query = """
    query listRedirects($first: Int!) {
        urlRedirects(first: $first) {
            edges {
                node {
                    id
                    path
                    target
                }
            }
        }
    }
    """
    
    variables = {"first": limit}
    
    response = client.execute_graphql(query, variables)
    data = response.get("data", {})
    
    if "urlRedirects" in data:
        redirects = []
        for edge in data["urlRedirects"]["edges"]:
            redirects.append(edge["node"])
        return redirects
    return []


def delete_redirect(redirect_id: str) -> bool:
    """Delete a URL redirect."""
    client = ShopifyClient()
    
    # Ensure proper GID format
    if not redirect_id.startswith("gid://"):
        redirect_id = f"gid://shopify/UrlRedirect/{redirect_id}"
    
    mutation = """
    mutation deleteUrlRedirect($id: ID!) {
        urlRedirectDelete(id: $id) {
            deletedUrlRedirectId
            userErrors {
                field
                message
            }
        }
    }
    """
    
    variables = {"id": redirect_id}
    
    result = client.execute_graphql(mutation, variables)
    
    # Check for errors
    if not client.check_user_errors(result, "urlRedirectDelete"):
        return False
    
    data = result.get('data', {}).get('urlRedirectDelete', {})
    return data is not None and 'deletedUrlRedirectId' in data


def main():
    parser = argparse.ArgumentParser(description="Manage Shopify URL redirects")
    parser.add_argument("--action", choices=["create", "list", "delete"], required=True,
                        help="Action to perform")
    parser.add_argument("--from", dest="from_path", help="Source path to redirect from")
    parser.add_argument("--to", dest="to_path", help="Target path to redirect to")
    parser.add_argument("--id", help="Redirect ID for deletion")
    parser.add_argument("--limit", type=int, default=50, help="Limit for listing redirects")
    
    args = parser.parse_args()
    
    if args.action == "create":
        if not args.from_path or not args.to_path:
            parser.error("--from and --to are required for create action")
        
        redirect = create_redirect(args.from_path, args.to_path)
        if redirect:
            print(f"✅ Successfully created redirect:")
            print(f"   From: {redirect['path']}")
            print(f"   To: {redirect['target']}")
            print(f"   ID: {redirect['id']}")
        else:
            print("❌ Failed to create redirect")
            sys.exit(1)
    
    elif args.action == "list":
        redirects = list_redirects(args.limit)
        if redirects:
            print(f"Found {len(redirects)} redirects:")
            for redirect in redirects:
                print(f"\n{redirect['id']}")
                print(f"  From: {redirect['path']}")
                print(f"  To: {redirect['target']}")
        else:
            print("No redirects found")
    
    elif args.action == "delete":
        if not args.id:
            parser.error("--id is required for delete action")
        
        if delete_redirect(args.id):
            print(f"✅ Successfully deleted redirect: {args.id}")
        else:
            print("❌ Failed to delete redirect")
            sys.exit(1)


if __name__ == "__main__":
    main()