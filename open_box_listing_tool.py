# open_box_listing_tool.py
"""Open‑Box Listing Tool for iDrinkCoffee.com (single product)

This module exposes a `create_open_box_listing_single` function designed to be
registered as a tool in *simple_agent.py*. It re‑uses the proven helper
functions in **duplicate.py** but adapts the workflow for one‑off Open Box
(O/B) listings instead of CSV‑driven bulk jobs.

Usage (tool definition example – add to TOOLS array in *simple_agent.py*):

```python
{
    "name": "create_open_box_listing_single",
    "type": "function",
    "function": {
        "name": "create_open_box_listing_single",
        "description": "Duplicate a single product as an Open Box listing. The caller must supply a product identifier (title, handle, ID or SKU), the unit’s serial number, a condition suffix (e.g. 'Excellent', 'Scratch & Dent'), **and** either an explicit price or a discount percentage.",
        "parameters": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Product title / handle / numeric ID / SKU to duplicate"},
                "serial_number": {"type": "string", "description": "Unit serial number to embed in title & description."},
                "suffix": {"type": "string", "description": "Condition descriptor appended to the title (e.g. 'Excellent')."},
                "price": {"type": "number", "description": "Explicit Open Box price in CAD dollars.", "default": None},
                "discount_pct": {"type": "number", "description": "Percent discount off the product’s higher of price / compareAtPrice.", "default": None}
            },
            "required": ["identifier", "serial_number", "suffix"]
        }
    }
}
```

Register the Python function with `simple_agent.py` *before* the agent loop:

```python
from open_box_listing_tool import create_open_box_listing_single
```

---

Dependencies
------------
* `duplicate.py` must live in `PYTHONPATH` – we import its helper routines.
* `SHOPIFY_ADMIN_TOKEN`, `SHOP_DOMAIN`, and `API_VERSION` environment
  variables **must** be set (identical to *duplicate.py*).
"""

from __future__ import annotations

import os
import time
import logging
from typing import Dict, Optional, List

# Re‑use the robust HTTP session & helpers already battle‑tested in duplicate.py
from duplicate import (
    fetch_product_details,
    duplicate_product,
    update_product_details,
    update_variant_details,
    set_inventory_to_one,
    clear_bundle_product_ids,
    remove_extra_variants,
    write_kit_csv,
)

# Additional helper to locate a product when the caller provides a title or SKU.
from duplicate import http, SHOP_DOMAIN, API_VERSION, HEADERS  # type: ignore

# ---------------------------------------------------------------------------
# Utility: resolve identifier → numeric product_id
# ---------------------------------------------------------------------------

def _resolve_product_id(identifier: str) -> Optional[str]:
    """Accept numeric ID, global ID, handle, or SKU and return numeric product ID."""
    identifier = identifier.strip()
    # 1. If already numeric → done
    if identifier.isdigit():
        return identifier
    # 2. If global ID (gid://shopify/Product/12345)
    if identifier.startswith("gid://"):
        return identifier.split("/")[-1]

    # 3. Search by handle OR title OR variant SKU via Storefront search_query
    query_by_title_or_handle = (
        f"query ($search:String!) {{\n  products(first: 1, query: $search) {{\n    edges {{ node {{ id handle title }} }}\n  }}\n}}"
    )
    variables = {"search": identifier.replace("\"", "\\\"")}
    try:
        resp = http.post(
            f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json",
            headers=HEADERS,
            json={"query": query_by_title_or_handle, "variables": variables},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        edges = (
            data.get("data", {})
            .get("products", {})
            .get("edges", [])
        )
        if edges:
            return edges[0]["node"]["id"].split("/")[-1]
    except Exception as e:
        logging.error(f"Error resolving identifier '{identifier}': {e}")
    return None

# ---------------------------------------------------------------------------
# Main tool function
# ---------------------------------------------------------------------------

def create_open_box_listing_single(
    identifier: str,
    serial_number: str,
    suffix: str,
    price: Optional[float] = None,
    discount_pct: Optional[float] = None,
    note: Optional[str] = None,
) -> Dict[str, str | bool]:
    """Duplicate *identifier* as a one‑off Open Box listing.

    Returns
    -------
    dict with keys:
      * success (bool)
      * new_product_id (str | None)
      * message (str)
    """

    # ---------------------------------------------------------------------
    # 0. Sanity checks
    # ---------------------------------------------------------------------
    if price is None and discount_pct is None:
        return {
            "success": False,
            "new_product_id": None,
            "message": "Provide either an explicit price or a discount_pct.",
        }
    if price is not None and price <= 0:
        return {
            "success": False,
            "new_product_id": None,
            "message": "Price must be positive.",
        }
    if discount_pct is not None and not (0 < discount_pct < 100):
        return {
            "success": False,
            "new_product_id": None,
            "message": "discount_pct should be between 0 and 100.",
        }

    # ---------------------------------------------------------------------
    # 1. Resolve & fetch original product
    # ---------------------------------------------------------------------
    product_id = _resolve_product_id(identifier)
    if not product_id:
        return {"success": False, "new_product_id": None, "message": "Product not found."}

    original = fetch_product_details(product_id)
    if not original:
        return {
            "success": False,
            "new_product_id": None,
            "message": f"Could not fetch product {product_id} details.",
        }

    orig_title: str = original["title"]
    orig_tags: List[str] = original.get("tags", [])
    variant_node = original["variants"]["edges"][0]["node"]
    orig_price = float(variant_node["price"] or 0)
    orig_compare = float(variant_node.get("compareAtPrice") or 0)
    orig_price_base = max(orig_price, orig_compare)
    orig_sku = variant_node.get("sku", "")

    # ---------------------------------------------------------------------
    # 2. Construct new listing metadata
    # ---------------------------------------------------------------------
    suffix_clean = suffix.strip()
    new_title = f"{orig_title} |{serial_number}| - {suffix_clean}"

    if price is not None:
        new_price = f"{price:.2f}"
    else:
        new_price = f"{orig_price_base * (1 - discount_pct / 100):.2f}"

    # SKU strategy: OB-<yyMM>-<serial>-<orig_sku>
    date_code = time.strftime("%y%m")  # e.g., '2505' for May 2025
    new_sku = f"OB-{date_code}-{serial_number}-{orig_sku}" if orig_sku else f"OB-{date_code}-{serial_number}"

    # Tag logic from duplicate.py
    today_mmddyyyy = time.strftime("%m%d%Y")
    yymm = time.strftime("%y%m")
    tag_suffix = suffix_clean.lower().replace(" ", "-")
    extra_tags = [tag_suffix, "open-box", "openbox", f"ob{today_mmddyyyy}", f"ob{yymm}"]
    tags = list({*orig_tags, *extra_tags})  # deduplicate

    # Use user-supplied note if provided, otherwise no note
    note = note if note else None

    # ---------------------------------------------------------------------
    # 3. Duplicate product (draft, include images)
    # ---------------------------------------------------------------------
    new_product_id = duplicate_product(product_id, new_title, "duplicated_products_single.csv")
    if not new_product_id:
        return {
            "success": False,
            "new_product_id": None,
            "message": "productDuplicate mutation failed (see logs).",
        }

    # ---------------------------------------------------------------------
    # 4. Post‑duplicate fixes – mirror duplicate.py flow
    # ---------------------------------------------------------------------
    #   a. ensure bundle metafield removed
    clear_bundle_product_ids(new_product_id)

    #   b. fetch duplicated details + variant ID
    dup_details = fetch_product_details(new_product_id)
    if not dup_details:
        return {
            "success": False,
            "new_product_id": None,
            "message": "Could not fetch duplicated product details.",
        }
    new_variant_id = dup_details["variants"]["edges"][0]["node"]["id"]

    #   c. remove extra variants, keep default → inventory 1
    if not remove_extra_variants(new_product_id, new_variant_id):
        return {
            "success": False,
            "new_product_id": new_product_id,
            "message": "Variant cleanup failed.",
        }
    set_inventory_to_one(new_variant_id)

    #   d. Update product tags + description
    if not update_product_details(new_product_id, tags, note):
        return {
            "success": False,
            "new_product_id": new_product_id,
            "message": "productUpdate failed.",
        }

    #   e. Update variant price / compareAt / SKU
    if not update_variant_details(
        variant_id=new_variant_id,
        price=new_price,
        compare_price=str(orig_price_base),
        new_sku=new_sku,
        new_product_id=new_product_id,
    ):
        return {
            "success": False,
            "new_product_id": new_product_id,
            "message": "productVariantsBulkUpdate failed.",
        }

    #   f. Kit CSV generation if SKU signals kit (“-K”)
    if "-K" in new_sku:
        write_kit_csv(
            kit_sku=new_sku,
            sku_code=new_sku,
            line_item_name=new_title,
            kit_title=new_title,
        )

    # ---------------------------------------------------------------------
    # 5. Success
    # ---------------------------------------------------------------------
    return {
        "success": True,
        "new_product_id": new_product_id,
        "message": f"Open Box listing created (Product ID {new_product_id}).",
    }
