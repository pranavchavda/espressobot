#!/usr/bin/env python3
"""Manage Breville MAP sales (MCP version).

This is a native MCP tool that supersedes the legacy ``manage_map_sales``
script.  The business logic was ported from ``/home/pranav/idc/tools/
manage_map_sales.py`` and adapted to the MCP modular style.

Highlights:
1.  Uses BaseMCPTool so it can be invoked by the MCP orchestrator.
2.  Talks to Shopify Admin GraphQL API 2025-07 only through
    ``ShopifyClient``.
3.  Only employs the ``productVariantsBulkUpdate`` mutation – no REST.
4.  Works off the 2025 Breville promo calendar markdown file shipped in
    this directory, parses the same tables as the legacy script and
    supports date-range reversion.
5.  Still offers a standalone CLI for local execution / dry-run testing
    (backwards compatible with the original interface).

The implementation purposefully avoids any I/O at import time so that it
is safe for serverless loading.
"""

from __future__ import annotations

import argparse
import re
import sys
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..base import BaseMCPTool, ShopifyClient

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
MONTH_MAP: Dict[str, int] = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}

CalendarData = Dict[str, List[Dict[str, str]]]


# ---------------------------------------------------------------------------
# Core logic – extracted from legacy tool and made class-friendly
# ---------------------------------------------------------------------------
class BrevilleMapCalendar:
    """Parse the enhanced Breville sales calendar markdown file."""

    def __init__(self, calendar_file: Path) -> None:
        self.calendar_file: Path = calendar_file
        self.sales_data: CalendarData = {}
        self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not self.calendar_file.exists():
            raise FileNotFoundError(f"Calendar file not found: {self.calendar_file}")

        date_header_re = re.compile(r"^## (.+ - .+)$")
        current_range: Optional[str] = None

        with self.calendar_file.open() as fh:
            for line in fh:
                line = line.rstrip("\n")
                header_match = date_header_re.match(line)
                if header_match:
                    current_range = header_match.group(1)
                    self.sales_data[current_range] = []
                    continue

                if (
                    current_range
                    and line.startswith("|")
                    and not line.startswith("| Product")
                    and not line.startswith("|---")
                ):
                    # Split markdown table row, ignore the first/last pipes.
                    cells = [c.strip() for c in line.split("|")[1:-1]]
                    if len(cells) < 8:
                        # Row is malformed – skip.
                        continue
                    (
                        product_title,
                        colour,
                        sku,
                        regular_price,
                        sale_price,
                        discount,
                        product_id,
                        variant_id,
                    ) = cells[:8]

                    self.sales_data[current_range].append(
                        {
                            "product_title": product_title,
                            "color": colour,
                            "sku": sku,
                            "regular_price": float(regular_price.replace("$", "").replace(",", "")),
                            "sale_price": float(sale_price.replace("$", "").replace(",", "")),
                            "discount": discount,
                            "product_id": product_id,
                            "variant_id": variant_id,
                        }
                    )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def _parse_date_range(self, dr: str) -> Tuple[date, date]:
        start_str, end_str = dr.split(" - ")

        start_day, start_mon = start_str.split(" ")
        end_day, end_mon = end_str.split(" ")

        start_month_num = MONTH_MAP[start_mon]
        end_month_num = MONTH_MAP[end_mon]

        current_year = date.today().year
        start_year = current_year
        end_year = current_year
        if start_month_num == 12 and end_month_num == 1:
            end_year += 1

        return (
            date(start_year, start_month_num, int(start_day)),
            date(end_year, end_month_num, int(end_day)),
        )

    def active_sales_for(self, on: date) -> Tuple[List[Dict[str, str]], Optional[str]]:
        active: List[Dict[str, str]] = []
        active_range: Optional[str] = None
        for dr, products in self.sales_data.items():
            start, end = self._parse_date_range(dr)
            if start <= on <= end:
                active.extend(products)
                active_range = dr
        return active, active_range

    def sale_end_iso(self, dr: str) -> str:
        """Return ISO8601 Z time for 23:59:59 on the range's end date."""
        _, end_d = self._parse_date_range(dr)
        end_dt = datetime.combine(end_d, datetime.max.time()).replace(tzinfo=timezone.utc)
        return end_dt.isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# MCP Tool implementation
# ---------------------------------------------------------------------------
class ManageMapSalesTool(BaseMCPTool):
    """Manage Breville MAP sales based on 2025 calendar."""

    name = "manage_map_sales"
    description = "Apply or revert Breville MAP (Minimum Advertised Price) sales."
    context = (
        "Uses the 2025 enhanced Breville sales calendar to apply or revert MAP prices. "
        "Supports actions: check, apply, revert, summary."
    )

    input_schema = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["check", "apply", "revert", "summary"]},
            "date": {"type": "string", "description": "Date (YYYY-MM-DD) for operations"},
            "date_range": {"type": "string", "description": "Date range header for reversion"},
            "dry_run": {"type": "boolean", "default": False},
        },
        "required": ["action"],
    }

    # ------------------------------------------------------------------
    # Life-cycle
    # ------------------------------------------------------------------
    def __init__(self) -> None:
        super().__init__()
        self.calendar = BrevilleMapCalendar(
            Path(__file__).with_suffix("").parent / "breville_espresso_sales_2025_enhanced.md"
        )
        self.client = ShopifyClient()  # Already points to 2025-07

    # ------------------------------------------------------------------
    # Base entry point – async for compatibility with orchestrator
    # ------------------------------------------------------------------
    async def execute(self, action: str, **kwargs):  # type: ignore[override]
        action_map = {
            "check": self._check_action,
            "apply": self._apply_action,
            "revert": self._revert_action,
            "summary": self._summary_action,
        }
        if action not in action_map:
            return {"success": False, "error": f"Unsupported action: {action}"}
        try:
            return action_map[action](**kwargs)
        except Exception as exc:  # pylint: disable=broad-except
            return {"success": False, "error": str(exc), "action": action}

    # ------------------------------------------------------------------
    # Shopify helpers (mutations / queries)
    # ------------------------------------------------------------------
    PRODUCT_SEARCH_Q = """
    query searchBySku($query: String!) {
        products(first: 5, query: $query) {
            edges {
                node {
                    id
                    tags
                    variants(first: 10) {
                        edges {
                            node {
                                id
                                sku
                                price
                                compareAtPrice
                            }
                        }
                    }
                }
            }
        }
    }
    """

    PRODUCT_VARIANT_BULK_MUTATION = """
    mutation bulkUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
        productVariantsBulkUpdate(productId: $productId, variants: $variants) {
            productVariants { id price compareAtPrice }
            userErrors { field message }
        }
    }
    """

    PRODUCT_UPDATE_METAFIELD_MUTATION = """
    mutation productUpdate($input: ProductInput!) {
        productUpdate(input: $input) {
            product { id }
            userErrors { field message }
        }
    }
    """

    # ------------------------------------------------------------------
    # Action implementations (sync for simplicity)
    # ------------------------------------------------------------------
    def _check_action(self, **kwargs):
        check_date: date = (
            datetime.strptime(kwargs.get("date"), "%Y-%m-%d").date() if kwargs.get("date") else date.today()
        )
        sales, range_header = self.calendar.active_sales_for(check_date)
        return {
            "success": True,
            "date": str(check_date),
            "sale_period": range_header,
            "count": len(sales),
            "sales": sales,
        }

    def _apply_action(self, **kwargs):
        dry_run: bool = kwargs.get("dry_run", False)
        target_date: date = (
            datetime.strptime(kwargs.get("date"), "%Y-%m-%d").date() if kwargs.get("date") else date.today()
        )
        active_sales, active_range = self.calendar.active_sales_for(target_date)
        if not active_sales:
            return {"success": True, "message": f"No Breville sales on {target_date}"}

        sale_end_iso = self.calendar.sale_end_iso(active_range)  # type: ignore[arg-type]
        stats = {"updated": 0, "already_on_sale": 0, "not_found": 0, "not_map": 0}
        product_ids_needing_end_date = set()

        for product in active_sales:
            sku = product["sku"]
            search_res = self.client.execute_graphql(self.PRODUCT_SEARCH_Q, {"query": f"sku:{sku} status:active"})
            product_info = self._extract_product_info(search_res, sku)
            if not product_info:
                stats["not_found"] += 1
                continue

            if "BREMAP" not in product_info["tags"]:
                stats["not_map"] += 1
                continue

            product_ids_needing_end_date.add(product_info["product_id"])

            # Already on sale?
            if (
                product_info["compare_at"]
                and abs(product_info["current_price"] - product["sale_price"]) < 0.01
            ):
                stats["already_on_sale"] += 1
                continue

            if dry_run:
                stats["updated"] += 1
                continue

            variables = {
                "productId": product_info["product_id"],
                "variants": [
                    {
                        "id": product_info["variant_id"],
                        "price": str(product["sale_price"]),
                        "compareAtPrice": str(product["regular_price"]),
                    }
                ],
            }
            mutation_res = self.client.execute_graphql(self.PRODUCT_VARIANT_BULK_MUTATION, variables)
            if not self.client.check_user_errors(mutation_res, "productVariantsBulkUpdate"):
                continue
            stats["updated"] += 1

        # Set sale end metafield on parent products
        if not dry_run and product_ids_needing_end_date:
            for pid in product_ids_needing_end_date:
                self._update_sale_end_metafield(pid, sale_end_iso)

        return {"success": True, "details": stats, "sale_end": sale_end_iso, "dry_run": dry_run}

    def _revert_action(self, **kwargs):
        date_range: str = kwargs.get("date_range") or ""
        dry_run: bool = kwargs.get("dry_run", False)
        if date_range not in self.calendar.sales_data:
            return {
                "success": False,
                "error": f"Date range '{date_range}' not in Breville calendar",
                "available": list(self.calendar.sales_data.keys()),
            }

        products = self.calendar.sales_data[date_range]
        stats = {"reverted": 0, "not_on_sale": 0, "not_found": 0}
        product_ids: set[str] = set()
        for product in products:
            sku = product["sku"]
            res = self.client.execute_graphql(self.PRODUCT_SEARCH_Q, {"query": f"sku:{sku} status:active"})
            info = self._extract_product_info(res, sku)
            if not info:
                stats["not_found"] += 1
                continue
            product_ids.add(info["product_id"])
            if not info["compare_at"]:
                stats["not_on_sale"] += 1
                continue
            if dry_run:
                stats["reverted"] += 1
                continue
            variables = {
                "productId": info["product_id"],
                "variants": [
                    {"id": info["variant_id"], "price": str(product["regular_price"]), "compareAtPrice": None}
                ],
            }
            mutation_res = self.client.execute_graphql(self.PRODUCT_VARIANT_BULK_MUTATION, variables)
            if not self.client.check_user_errors(mutation_res, "productVariantsBulkUpdate"):
                continue
            stats["reverted"] += 1
        # Clear metafield
        if not dry_run:
            for pid in product_ids:
                self._update_sale_end_metafield(pid, "")
        return {"success": True, "details": stats, "dry_run": dry_run}

    def _summary_action(self, **_kw):
        today = date.today()
        summary = []
        for dr in sorted(self.calendar.sales_data.keys(), key=lambda r: self.calendar._parse_date_range(r)[0]):
            start, end = self.calendar._parse_date_range(dr)
            summary.append(
                {
                    "date_range": dr,
                    "products": len(self.calendar.sales_data[dr]),
                    "active": start <= today <= end,
                }
            )
        return {"success": True, "summary": summary}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_product_info(resp: Dict, sku: str):  # type: ignore[override]
        edges = resp.get("data", {}).get("products", {}).get("edges", [])
        for e in edges:
            node = e["node"]
            for v in node["variants"]["edges"]:
                variant = v["node"]
                if variant["sku"] == sku:
                    return {
                        "product_id": node["id"],
                        "variant_id": variant["id"],
                        "current_price": float(variant["price"]),
                        "compare_at": float(variant["compareAtPrice"]) if variant["compareAtPrice"] else None,
                        "tags": node["tags"],
                    }
        return None

    def _update_sale_end_metafield(self, product_id: str, sale_end: str) -> None:
        variables = {
            "input": {
                "id": product_id,
                "metafields": [
                    {
                        "namespace": "inventory",
                        "key": "ShappifySaleEndDate",
                        "value": sale_end,
                        "type": "single_line_text_field",
                    }
                ],
            }
        }
        res = self.client.execute_graphql(self.PRODUCT_UPDATE_METAFIELD_MUTATION, variables)
        self.client.check_user_errors(res, "productUpdate")


# ---------------------------------------------------------------------------
# CLI wrapper for backwards compatibility
# ---------------------------------------------------------------------------

def _cli() -> None:  # pragma: no cover – invoked manually
    parser = argparse.ArgumentParser(
        prog="manage_map_sales",
        description="Breville MAP sales manager (MCP edition)",
    )
    parser.add_argument("command", choices=["check", "apply", "revert", "summary"])
    parser.add_argument("--calendar", default=None, help="Override calendar file path")
    parser.add_argument("--date", help="Target date YYYY-MM-DD")
    parser.add_argument("--date-range", help="Date range header for revert")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    tool = ManageMapSalesTool()
    if args.calendar:
        tool.calendar = BrevilleMapCalendar(Path(args.calendar))

    result = {
        "check": lambda: tool._check_action(date=args.date),
        "apply": lambda: tool._apply_action(date=args.date, dry_run=args.dry_run),
        "revert": lambda: tool._revert_action(date_range=args.date_range, dry_run=args.dry_run),
        "summary": lambda: tool._summary_action(),
    }[args.command]()

    # Pretty-print result to stdout for human use.
    import json as _json

    print(_json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    _cli()
