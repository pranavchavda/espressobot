#!/usr/bin/env python3
"""
CLI script to bulk add variants to product
Created: 2025-07-03T23:00:29.140Z
Type: Ad-hoc tool
"""

#!/usr/bin/env python3
"""
add_variants_to_product.py

Add new variants to an existing product using productVariantsBulkCreate.
Usage:
python3 add_variants_to_product.py --product_gid gid://shopify/Product/8000956... --variants_json variants.json

variants.json example:
[
  {
    "price": "19.99",
    "sku": "ABC-1",
    "optionValues": [
       {"optionName": "Size", "value": "Small"}
    ]
  },
  { "price": "29.99", "sku": "ABC-2", "optionValues": [{"optionName":"Size","value":"Large"}] }
]

Environment variables SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN are required.
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List

from base import ShopifyClient, print_json


def main():
    parser = argparse.ArgumentParser(description="Add new variants to an existing product")
    parser.add_argument("--product_gid", required=True, help="GID or numeric ID of the product")
    parser.add_argument("--variants_json", required=True, help="Path to JSON array with variants input")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not os.path.isfile(args.variants_json):
        print(f"Error: Variants JSON not found -> {args.variants_json}", file=sys.stderr)
        sys.exit(1)

    with open(args.variants_json, "r", encoding="utf-8") as fh:
        variants: List[Dict[str, Any]] = json.load(fh)

    client = ShopifyClient()
    product_gid = client.normalize_id(args.product_gid)

    mutation = """
    mutation productVariantsBulkCreate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkCreate(productId: $productId, variants: $variants) {
            productVariants { id sku price }
            userErrors { field message }
        }
    }
    """

    variables = {"productId": product_gid, "variants": variants}
    result = client.execute_graphql(mutation, variables)

    if args.verbose:
        print_json(result)

    errors = result.get("data", {}).get("productVariantsBulkCreate", {}).get("userErrors")
    if errors:
        print("Variant creation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
    else:
        print("✅ Variants added successfully.")


if __name__ == "__main__":
    main()
