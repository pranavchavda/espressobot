"""
Atomic metafield updater for Shopify products via the `metafieldsSet` mutation.

This tool consolidates all metafield-writing use-cases for IDC into a single, schema-validated
endpoint that can be invoked by the MCP orchestrator.  It supports *both* single-product and
multi-product (batch) operations and automatically chunks requests to comply with the Shopify
limit of **25 metafields per metafieldsSet call**.

Key features
------------
1. JSON & Metaobject reference support – detects JSON values automatically when the `type` field
   is omitted, or you can explicitly set `type="metaobject_reference"` when passing a metaobject
   GID.
2. Handle, numeric ID **or** GID – the `product` field can be any of these and will be resolved
   server-side.
3. Strict, OpenAPI-/JSONSchema-compatible `input_schema` so the orchestrator can perform payload
   validation before execution.
4. Graceful value coercion – Python objects are serialised to JSON where appropriate and all
   other values are converted to strings, as expected by the Admin API.

Metafield examples
~~~~~~~~~~~~~~~~~~
• faq.content           → namespace: faq,   key: content,  type: json (auto-detected)
• specs.techjson        → namespace: specs, key: techjson, type: json (auto-detected)
• content.features_box  → namespace: content, key: features_box, type: metaobject_reference

Typical payloads
~~~~~~~~~~~~~~~~
Single product
```
{
  "product": "gid://shopify/Product/1234567890",
  "metafields": [
    {"namespace": "faq", "key": "content", "value": {"q": "A?", "a": "B"}},
    {"namespace": "specs", "key": "techjson", "value": {"amps": 15, "voltage": 110}}
  ]
}
```

Batch
```
{
  "updates": [
    {
      "product": "my-product-handle",
      "metafields": [
        {
          "namespace": "content",
          "key": "features_box",
          "type": "metaobject_reference",
          "value": "gid://shopify/Metaobject/987654321"
        }
      ]
    },
    {
      "product": "gid://shopify/Product/1122334455",
      "metafields": [
        {"namespace": "faq", "key": "content", "value": {"q": "What?", "a": "Yep"}}
      ]
    }
  ]
}
```
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Optional

# Make project root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from base import ShopifyClient
from ..base import BaseMCPTool

# ---------------------------------------------------------------------------
# JSONSCHEMA DEFINITIONS
# ---------------------------------------------------------------------------

INPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        # --------------------------------------------------------------
        # SINGLE-PRODUCT UPDATE PATH
        # --------------------------------------------------------------
        "product": {
            "type": "string",
            "description": "Identifier for the product you wish to update. Can be shopify GID, "
                           "numeric product ID, handle or SKU. Used with 'metafields' for single product update."
        },
        "metafields": {
            "type": "array",
            "description": "Metafields to write on the single product identified by 'product'. Use either this with 'product' OR use 'updates' for batch operations.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "namespace": {
                        "type": "string",
                        "description": "Metafield namespace (e.g. 'faq', 'specs', 'content')."
                    },
                    "key": {
                        "type": "string",
                        "description": "Metafield key (e.g. 'content', 'techjson', 'features_box')."
                    },
                    "type": {
                        "type": "string",
                        "description": (
                            "Explicit Shopify metafield type. Optional – when omitted the tool will attempt "
                            "to infer it. Common values: 'json', 'single_line_text_field', "
                            "'metaobject_reference'."
                        )
                    },
                    "value": {
                        "description": (
                            "Metafield value. Accepts string, number, boolean, object or array.  When passing "
                            "objects/arrays the tool will JSON-encode them automatically if `type` is 'json'."
                        )
                    }
                },
                "required": ["namespace", "key", "value"]
            },
        },
        # --------------------------------------------------------------
        # BATCH UPDATE PATH
        # --------------------------------------------------------------
        "updates": {
            "type": "array",
            "description": "Array of product + metafields tuples for batch updates. Use either this OR use 'product' with 'metafields' for single operations.",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "product": {
                        "type": "string",
                        "description": "Product identifier (handle, ID, GID or SKU)."
                    },
                    "metafields": {
                        # Inline the object schema to avoid reference-resolution issues in the
                        # OpenAPI generator. Explicitly defining `items` ensures that the path
                        # `updates[].metafields` validates as an **array of objects** with the
                        # expected required keys.
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "namespace": {
                                    "type": "string",
                                    "description": "Metafield namespace (e.g. 'faq', 'specs', 'content')."
                                },
                                "key": {
                                    "type": "string",
                                    "description": "Metafield key (e.g. 'content', 'techjson', 'features_box')."
                                },
                                "type": {
                                    "type": "string",
                                    "description": (
                                        "Explicit Shopify metafield type. Optional – when omitted the tool will attempt "
                                        "to infer it. Common values: 'json', 'single_line_text_field', "
                                        "'metaobject_reference'."
                                    )
                                },
                                "value": {
                                    "description": (
                                        "Metafield value. Accepts string, number, boolean, object or array.  When passing "
                                        "objects/arrays the tool will JSON-encode them automatically if `type` is 'json'."
                                    )
                                }
                            },
                            "required": ["namespace", "key", "value"]
                        },
                        "minItems": 1
                    },
                },
                "required": ["product", "metafields"],
            },
            "minItems": 1,
        },
    },
    # NOTE: Removed oneOf constraint as it's not supported at top level by Claude's API
    # The validation logic is now handled in the execute method
}

# ---------------------------------------------------------------------------
# TOOL IMPLEMENTATION
# ---------------------------------------------------------------------------
class UpdateMetafieldsTool(BaseMCPTool):
    """Set metafields on products atomically using the Shopify `metafieldsSet` mutation."""

    # Meta
    name = "update_metafields"
    description = (
        "Atomically set one or more metafields on one or more Shopify products via the "
        "Admin GraphQL API's metafieldsSet mutation.  Supports JSON and metaobject_reference "
        "types out-of-the-box."
    )
    input_schema: Dict[str, Any] = INPUT_SCHEMA

    # --------------------------------------------------------------------
    # Public entry-point (invoked by MCP orchestrator)
    # --------------------------------------------------------------------
    async def execute(
        self,
        product: Optional[str] = None,
        metafields: Optional[List[Dict[str, Any]]] = None,
        updates: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Validate input, construct metafieldsSet payloads, issue API calls and
        return a summary dict.
        """
        try:
            client = ShopifyClient()
            all_inputs: List[Dict[str, Any]] = []

            # ----- Validate input parameters (replaces oneOf constraint) -----------------
            if updates and (product or metafields):
                return {
                    "success": False,
                    "error": "Cannot use 'updates' together with 'product' or 'metafields'. Choose one approach.",
                }
            
            if not updates and not (product and metafields):
                return {
                    "success": False,
                    "error": "Provide either (product & metafields) or 'updates'.",
                }

            # ----- Build the input list --------------------------------------------------
            if updates:
                for entry in updates:
                    all_inputs.extend(self._build_inputs(client, entry["product"], entry["metafields"]))
            else:
                all_inputs.extend(self._build_inputs(client, product, metafields))

            if not all_inputs:
                return {"success": False, "error": "No metafields to update."}

            # ----- Chunk + send ----------------------------------------------------------
            CHUNK_SIZE = 25  # API hard limit
            chunks = [all_inputs[i : i + CHUNK_SIZE] for i in range(0, len(all_inputs), CHUNK_SIZE)]

            updated_count = 0
            for chunk in chunks:
                result = self._metafields_set(client, chunk)
                if not result["success"]:
                    return result  # Bubble-up the error immediately
                updated_count += len(result.get("metafields", []))

            return {"success": True, "updated": updated_count}
        except Exception as exc:  # pragma: no cover – ensures we always bubble an error dict
            return {"success": False, "error": str(exc)}

    # --------------------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------------------
    def _build_inputs(
        self,
        client: ShopifyClient,
        product_identifier: str,
        metafields: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Transform the user-supplied metafields into MetafieldsSetInput objects."""
        gid = client.resolve_product_id(product_identifier)
        if not gid:
            raise ValueError(f"Product not found: {product_identifier}")

        inputs: List[Dict[str, Any]] = []
        for mf in metafields:
            m_type: str = mf.get("type", "")
            value: Any = mf.get("value")

            # --- Infer type when not provided ----------------------------------------
            if not m_type:
                if isinstance(value, (dict, list)):
                    m_type = "json"
                else:
                    m_type = "single_line_text_field"

            # --- Coerce value based on type ------------------------------------------
            if m_type == "json":
                # Value must be a JSON *string* when sent to the API
                if not isinstance(value, str):
                    value = json.dumps(value, separators=(",", ":"))
            else:
                # Convert everything else to string – API expects this for all scalar types
                value = str(value)

            inputs.append(
                {
                    "ownerId": gid,
                    "namespace": mf["namespace"],
                    "key": mf["key"],
                    "type": m_type,
                    "value": value,
                }
            )
        return inputs

    def _metafields_set(self, client: ShopifyClient, inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute the metafieldsSet mutation and return result dict."""
        mutation = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) {
            metafields { id namespace key type value }
            userErrors { field message code }
          }
        }
        """
        response = client.execute_graphql(mutation, {"metafields": inputs})

        result_data = response.get("data", {}).get("metafieldsSet", {})
        user_errors = result_data.get("userErrors")
        if user_errors:
            return {"success": False, "error": user_errors}

        return {"success": True, "metafields": result_data.get("metafields", [])}

    # --------------------------------------------------------------------
    # Basic connectivity test (used by MCP test harness)
    # --------------------------------------------------------------------
    async def test(self):  # type: ignore[override]
        try:
            client = ShopifyClient()
            _ = client.execute_graphql("{ shop { name } }")
            return {"status": "passed"}
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}


# ---------------------------------------------------------------------------
# MCP registration hook (called by orchestrator)
# ---------------------------------------------------------------------------

def _register():
    return UpdateMetafieldsTool()
