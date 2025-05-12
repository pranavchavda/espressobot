import os
import httpx
import asyncio
from typing import Dict, Any, Optional

# Helper: fetch a Shopify product by title or SKU
async def fetch_product(identifier: str) -> Optional[Dict[str, Any]]:
    """Fetch a Shopify product by title or SKU (case-insensitive). Returns the first match or None."""
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "")
    access_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
    api_version = os.environ.get("SHOPIFY_API_VERSION", "2025-04")
    if not shop_url or not access_token:
        raise ValueError("Missing Shopify credentials")
    if not shop_url.startswith("http"):
        shop_url = f"https://{shop_url}"
    endpoint = f"{shop_url.rstrip('/')}/admin/api/{api_version}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    # Try by title first
    query = '''query ($query: String!) {\n  products(first: 5, query: $query) {\n    edges {\n      node {\n        id\n        title\n        handle\n        variants(first: 10) {\n          edges {\n            node {\n              id\n              sku\n              title\n            }\n          }\n        }\n      }\n    }\n  }\n}'''
    # Search by title or SKU
    search_queries = [f'title:"{identifier}"', f'sku:{identifier}']
    for sq in search_queries:
        variables = {"query": sq}
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
            resp = await client.post(endpoint, json={"query": query, "variables": variables}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            edges = data.get("data", {}).get("products", {}).get("edges", [])
            if edges:
                return edges[0]["node"]
    return None

async def create_open_box_listing(identifier: str, title_prefix: Optional[str] = None, tag: Optional[str] = "Open Box", price_discount_pct: Optional[float] = None) -> dict:
    """
    Duplicate a product and create an Open Box listing using productDuplicate and follow-up mutations, matching duplicate.py logic. Prompts for missing info if needed.
    """
    import asyncio
    import re
    # 1. Fetch product by identifier (title or SKU)
    product = await fetch_product(identifier)
    if not product:
        return {"error": f"No product found for '{identifier}'"}
    orig_title = product["title"]
    orig_id = product["id"]
    # 2. Prepare Open Box title
    ob_title = f"{title_prefix} {orig_title}".strip() if title_prefix else None
    if not ob_title:
        return {"needs_input": "title_prefix", "prompt": f"What should the Open Box title prefix be for '{orig_title}'?"}
    # 3. Duplicate the product using productDuplicate
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "")
    access_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
    api_version = os.environ.get("SHOPIFY_API_VERSION", "2025-04")
    endpoint = f"{shop_url.rstrip('/')}/admin/api/{api_version}/graphql.json"
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    mutation_dup = '''mutation DuplicateProduct($productId: ID!, $newTitle: String!, $includeImages: Boolean!, $newStatus: ProductStatus!) {\n  productDuplicate(productId: $productId, newTitle: $newTitle, includeImages: $includeImages, newStatus: $newStatus) {\n    newProduct { id }\n    userErrors { field message }\n  }\n}'''
    variables_dup = {
        "productId": orig_id,
        "newTitle": ob_title,
        "includeImages": True,
        "newStatus": "DRAFT"
    }
    async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
        resp = await client.post(endpoint, json={"query": mutation_dup, "variables": variables_dup}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        payload = data.get("data", {}).get("productDuplicate")
        if not payload or payload.get("userErrors"):
            return {"error": f"Error duplicating product: {payload.get('userErrors') if payload else data}"}
        new_product_gid = payload["newProduct"]["id"]
        new_product_id = new_product_gid.split("/")[-1]
    # 4. Update product details (tags, description, etc.)
    mutation_update = '''mutation UpdateProduct($input: ProductInput!) {\n  productUpdate(input: $input) {\n    product { id tags descriptionHtml }\n    userErrors { field message }\n  }\n}'''
    # Fetch original tags and add Open Box tag
    orig_tags = product.get("tags", [])
    tags = orig_tags + ([tag] if tag and tag not in orig_tags else [])
    # Description: fetch original description if possible
    orig_desc = product.get("descriptionHtml", "")
    notes = "Open Box listing. See description for details."
    updated_body_html = f"<strong>{notes}</strong>\n{orig_desc}"
    variables_update = {
        "input": {
            "id": new_product_gid,
            "tags": tags,
            "descriptionHtml": updated_body_html
        }
    }
    async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
        resp = await client.post(endpoint, json={"query": mutation_update, "variables": variables_update}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors") or data.get("data", {}).get("productUpdate", {}).get("userErrors"):
            return {"error": f"Error updating duplicated product: {data}"}
    # 5. Update variant(s) using productVariantsBulkUpdate
    # Get variants from original product
    orig_variants = product.get("variants", {}).get("edges", [])
    if not orig_variants:
        return {"error": "Original product has no variants to duplicate."}
    variant_inputs = []
    for v in orig_variants:
        node = v["node"]
        orig_sku = node.get("sku")
        orig_price = node.get("price")
        new_sku = f"{orig_sku}-OB" if orig_sku else None
        new_price = None
        if price_discount_pct and orig_price:
            try:
                new_price = str(round(float(orig_price) * (1 - price_discount_pct/100), 2))
            except Exception:
                new_price = orig_price
        else:
            new_price = orig_price
        # Bulk update input
        variant_inputs.append({
            "sku": new_sku,
            "price": new_price
        })
    # Fetch new product's variants to get their IDs
    query_new_variants = '''query GetVariants($id: ID!) {\n  product(id: $id) {\n    variants(first: 10) { edges { node { id } } }\n  }\n}'''
    variables_qv = {"id": new_product_gid}
    async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
        resp = await client.post(endpoint, json={"query": query_new_variants, "variables": variables_qv}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        new_variants = data.get("data", {}).get("product", {}).get("variants", {}).get("edges", [])
        if not new_variants or len(new_variants) != len(variant_inputs):
            return {"error": "Could not match new product variants for bulk update."}
        for i, v in enumerate(new_variants):
            variant_inputs[i]["id"] = v["node"]["id"]
    mutation_bulk = '''mutation productVariantsBulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {\n  productVariantsBulkUpdate(productId: $productId, variants: $variants) {\n    product { id }\n    productVariants { id price sku compareAtPrice inventoryItem { tracked } }\n    userErrors { field message }\n  }\n}'''
    variables_bulk = {
        "productId": new_product_gid,
        "variants": variant_inputs
    }
    async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
        resp = await client.post(endpoint, json={"query": mutation_bulk, "variables": variables_bulk}, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if data.get("errors") or data.get("data", {}).get("productVariantsBulkUpdate", {}).get("userErrors"):
            return {"error": f"Error updating variants: {data}"}
    return {"success": True, "new_product_id": new_product_id, "new_title": ob_title}
