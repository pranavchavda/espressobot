#!/usr/bin/env python3
"""
A CLI script to update existing Shopify product
Created: 2025-07-03T23:00:20.282Z
Type: Ad-hoc tool
"""

#!/usr/bin/env python3
"""
update_full_product.py

Update an existing Shopify product with full content: title, description, tags, metafields, variants, media, etc.

Usage examples:

# Basic update with JSON payload
python3 update_full_product.py --product_gid gid://shopify/Product/8000956006434 --content_json ./payload.json

# Verbose / debug
DEBUG=true python3 update_full_product.py --product_gid 8000956006434 --content_json ./payload.json --verbose

Environment variables required:
- SHOPIFY_SHOP_URL  (e.g. mystore.myshopify.com)
- SHOPIFY_ACCESS_TOKEN (Admin API access token)

JSON structure example (payload.json):
{
  "title": "My Updated Product",
  "descriptionHtml": "<p>New description</p>",
  "productType": "Coffee Machine",
  "vendor": "La Marzocco",
  "tags": ["Commercial", "Espresso"],
  "metafields": [
     {"namespace": "global", "key": "warranty", "type": "single_line_text_field", "value": "2 years"}
  ],
  "variants": [
      {"id": "gid://shopify/ProductVariant/123", "price": "3999.00", "sku": "LM-123"},
      {"optionValues": [{"optionName": "Color", "value": "Black"}], "price": "4099.00", "sku": "LM-123-BLK"}
  ],
  "media": [
      {"originalSource": "https://cdn.example.com/images/new1.jpg", "alt": "Front view"},
      {"file_path": "./images/local_img.jpg", "alt": "Side view"}
  ]
}
"""

import argparse
import json
import mimetypes
import os
import sys
from typing import Any, Dict, List, Optional

from base import ShopifyClient, print_json

#######################################
# Helper functions
#######################################

def build_product_set_input(product_gid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map user payload into ProductSetInput structure."""
    allowed_top_level = [
        "title",
        "descriptionHtml",
        "productType",
        "vendor",
        "status",
        "templateSuffix",
        "requiresSellingPlan",
        "giftCard",
        "giftCardTemplateSuffix",
        "handle",
        "tags",
        "category",
        "seo",
    ]

    product_input: Dict[str, Any] = {"id": product_gid}

    for key in allowed_top_level:
        if key in payload:
            product_input[key] = payload[key]

    # metafields
    if "metafields" in payload:
        product_input["metafields"] = payload["metafields"]

    # variants
    if "variants" in payload:
        product_input["variants"] = payload["variants"]

    # files / media handled separately due to staged upload complexity
    return product_input


def upload_local_file_to_staged(client: ShopifyClient, file_path: str) -> Optional[str]:
    """Upload a local file using stagedUploadsCreate and return the resulting url if successful."""
    if not os.path.isfile(file_path):
        print(f"Error: File not found -> {file_path}", file=sys.stderr)
        return None

    filename = os.path.basename(file_path)
    mime, _ = mimetypes.guess_type(file_path)
    mime = mime or "image/jpeg"
    file_size = os.path.getsize(file_path)

    staged_mutation = """
    mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
        stagedUploadsCreate(input: $input) {
            stagedTargets {
                url
                resourceUrl
                parameters {
                    name
                    value
                }
            }
            userErrors { field message }
        }
    }
    """

    variables = {
        "input": [
            {
                "resource": "IMAGE",
                "filename": filename,
                "mimeType": mime,
                "httpMethod": "POST",
                "fileSize": file_size,
            }
        ]
    }

    result = client.execute_graphql(staged_mutation, variables)
    errors = result.get("data", {}).get("stagedUploadsCreate", {}).get("userErrors")
    if errors:
        print(f"Staged upload errors: {errors}", file=sys.stderr)
        return None

    target = result["data"]["stagedUploadsCreate"]["stagedTargets"][0]

    # Perform file upload (multipart/form-data)
    import requests

    upload_url = target["url"]
    params = {p["name"]: p["value"] for p in target["parameters"]}

    with open(file_path, "rb") as f:
        files = {"file": (filename, f, mime)}
        response = requests.post(upload_url, data=params, files=files)
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"File upload failed: {e}", file=sys.stderr)
            return None

    # After successful upload, resourceUrl can be used as originalSource
    return target["resourceUrl"]


def create_media_objects(client: ShopifyClient, product_gid: str, media_payload: List[Dict[str, Any]]):
    """Create or attach media objects to the product."""
    if not media_payload:
        return

    create_inputs = []
    for media in media_payload:
        original_source = media.get("originalSource")
        if not original_source and media.get("file_path"):
            original_source = upload_local_file_to_staged(client, media["file_path"])

        if not original_source:
            print(f"Skipping media without source: {media}", file=sys.stderr)
            continue

        create_inputs.append({
            "originalSource": original_source,
            "mediaContentType": media.get("mediaContentType", "IMAGE"),
            "alt": media.get("alt"),
        })

    if not create_inputs:
        return

    mutation = """
    mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
        productCreateMedia(productId: $productId, media: $media) {
            media {
                id
                alt
            }
            mediaUserErrors { field message }
        }
    }
    """
    variables = {"productId": product_gid, "media": create_inputs}
    result = client.execute_graphql(mutation, variables)

    errors = result.get("data", {}).get("productCreateMedia", {}).get("mediaUserErrors")
    if errors:
        print(f"Media creation errors: {errors}", file=sys.stderr)

#######################################
# Main script
#######################################

def main():
    parser = argparse.ArgumentParser(description="Update an existing Shopify product with full content, variants, metafields and media.")
    parser.add_argument("--product_gid", required=True, help="GID of the product to update (or numeric ID / handle).")
    parser.add_argument("--content_json", required=True, help="Path to JSON file containing update payload.")
    parser.add_argument("--verbose", action="store_true", help="Print resulting payload responses.")
    args = parser.parse_args()

    client = ShopifyClient()
    product_gid = client.normalize_id(args.product_gid)

    if not os.path.isfile(args.content_json):
        print(f"Error: JSON file not found -> {args.content_json}", file=sys.stderr)
        sys.exit(1)

    with open(args.content_json, "r", encoding="utf-8") as fh:
        payload: Dict[str, Any] = json.load(fh)

    product_input = build_product_set_input(product_gid, payload)

    mutation = """
    mutation productSet($input: ProductSetInput!, $sync: Boolean!) {
        productSet(input: $input, synchronous: $sync) {
            product { id title handle }
            userErrors { field message code }
        }
    }
    """

    variables = {"input": product_input, "sync": True}
    result = client.execute_graphql(mutation, variables)
    if args.verbose:
        print_json(result)

    errors = result.get("data", {}).get("productSet", {}).get("userErrors")
    if errors:
        print("ProductSet userErrors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        # continue to media processing anyway

    # media
    if "media" in payload:
        create_media_objects(client, product_gid, payload["media"])

    print("✅ Product update complete.")


if __name__ == "__main__":
    main()
