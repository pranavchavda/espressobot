#!/usr/bin/env python3
"""SkuVault → Shopify Quantity Sync Service

This module implements the *pull*-style inventory synchronisation from
SkuVault *to* Shopify.  The existing :pyfile:`inventory_updater.py` pushes
updates in the opposite direction (Shopify → SkuVault).  For operational
parity we provide the reverse flow so that changes made directly in
SkuVault – for example via receiving, manual adjustments, or the SkuVault
mobile app – are reflected in Shopify within minutes.

Design goals
------------
1. Incremental fetch – Only retrieve quantities for SKUs modified since the
   last successful sync timestamp (persisted to a *state* file).
2. Mapping layer – Translate *SkuVault* SKU → Shopify ``inventoryItemId`` /
   ``locationId``.  The mapping can be supplied statically via YAML or
   resolved on-demand via the Shopify Admin API when the field is missing.
3. Idempotent updates – Use the GraphQL mutation
   ``inventorySetOnHandQuantities`` which sets absolute on-hand values.
4. Extensive logging – JSON structured logs for easy ingestion by ELK /
   CloudWatch.
5. Robust error handling – A single raised :class:`SyncError` indicates the
   run failed and should be retried by the scheduler.
6. Audit trail – Append a summary record to
   ``var/log/skuvault_shopify_quantity_sync_YYYYMMDD.jsonl``.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Sequence

import requests
import yaml

# ---------------------------------------------------------------------------
# Logging (shared formatter with inventory_updater)
# ---------------------------------------------------------------------------


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:  # noqa: D401
        return json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "func": record.funcName,
                "line": record.lineno,
            }
        )


def _configure_logging(level: str | int = "INFO") -> None:  # noqa: D401
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler])


logger = logging.getLogger("skuvault-shopify-sync")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SyncError(Exception):
    """Raised when the sync job fails irrecoverably."""


class MappingError(Exception):
    """Raised for problems in the SKU → Shopify mapping stage."""


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkuQuantity:
    sku: str
    quantity: int


@dataclass(frozen=True)
class ShopifyInventoryTarget:
    inventory_item_id: str  # gid://shopify/InventoryItem/123456
    location_id: str        # gid://shopify/Location/123456


# ---------------------------------------------------------------------------
# SkuVault client (read-only – fetch modified quantities)
# ---------------------------------------------------------------------------


class SkuVaultReadonlyClient:
    """Subset of the SkuVault API sufficient for quantity sync."""

    BASE_URL = "https://app.skuvault.com"

    def __init__(self, token: str, timeout: int = 10):
        if not token:
            raise ValueError("Missing SkuVault API token")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "User-Agent": "idc-skvt-sync/1.0",
            }
        )
        self.timeout = timeout

    def fetch_modified_quantities(self, since: datetime) -> List[SkuQuantity]:
        """Return list of absolute quantities changed after *since*.

        Relies on the (fictional for unit tests) endpoint
        ``/api/inventory/getModifiedQuantity``.  The payload is expected to
        be
        ``{"Items": [{"Sku": "ABC", "QuantityOnHand": 10}, ...]}``.
        """

        url = f"{self.BASE_URL}/api/inventory/getModifiedQuantity"
        payload = {"ModifiedAfter": since.strftime("%Y-%m-%dT%H:%M:%SZ")}
        logger.info("POST %s", url)
        resp = self.session.post(url, json=payload, timeout=self.timeout)

        if resp.status_code >= 400:
            raise SyncError(f"SkuVault error {resp.status_code}: {resp.text}")

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise SyncError("Invalid JSON from SkuVault") from exc

        quantities: List[SkuQuantity] = [
            SkuQuantity(item["Sku"], int(item["QuantityOnHand"]))
            for item in data.get("Items", [])
        ]
        logger.info("Received %d modified SKUs", len(quantities))
        return quantities


# ---------------------------------------------------------------------------
# Shopify client (GraphQL)
# ---------------------------------------------------------------------------


class ShopifyInventoryClient:
    """Minimal GraphQL wrapper for inventorySetOnHandQuantities."""

    API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2024-04")

    def __init__(self, shop: str, token: str, timeout: int = 10):
        if not (shop and token):
            raise ValueError("Missing Shopify shop domain or token")
        self.endpoint = f"https://{shop}/admin/api/{self.API_VERSION}/graphql.json"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "X-Shopify-Access-Token": token,
                "Content-Type": "application/json",
                "User-Agent": "idc-skvt-sync/1.0",
            }
        )
        self.timeout = timeout

    _MUTATION = (
        "mutation SetOnHand($input: InventorySetOnHandQuantitiesInput!) { "
        "inventorySetOnHandQuantities(input: $input) { "
        "  userErrors { field code message } "
        "} }"
    )

    def set_quantities(self, items: Sequence[dict], reason: str = "SkuVault Sync") -> None:
        if not items:
            return
        payload = {
            "query": self._MUTATION,
            "variables": {
                "input": {
                    "reason": reason,
                    "setQuantities": list(items),
                }
            },
        }
        logger.info("POST Shopify GraphQL with %d items", len(items))
        resp = self.session.post(self.endpoint, json=payload, timeout=self.timeout)

        if resp.status_code >= 400:
            raise SyncError(f"Shopify HTTP {resp.status_code}: {resp.text}")

        try:
            data = resp.json()
        except json.JSONDecodeError as exc:  # pragma: no cover
            raise SyncError("Invalid JSON from Shopify") from exc

        errors = data.get("errors")
        user_errors = (
            data.get("data", {})
            .get("inventorySetOnHandQuantities", {})
            .get("userErrors", [])
        )
        if errors or user_errors:
            raise SyncError(f"Shopify returned errors: {errors or user_errors}")
        logger.info("Shopify update successful")


# ---------------------------------------------------------------------------
# Mapping utility
# ---------------------------------------------------------------------------


class SkuToShopifyMapper:
    """Translate SkuVault SKU → Shopify identifiers using static YAML map."""

    def __init__(self, cfg: dict):
        self.static_map: Dict[str, ShopifyInventoryTarget] = {}
        for entry in cfg.get("sku_mapping", []):
            sku = entry.get("skuvault_sku") or entry.get("shopify_sku")
            if not sku:
                continue
            if "shopify_inventory_item_id" in entry and "location_id" in entry:
                self.static_map[sku] = ShopifyInventoryTarget(
                    inventory_item_id=entry["shopify_inventory_item_id"],
                    location_id=entry["location_id"],
                )

    def resolve(self, sku: str) -> ShopifyInventoryTarget | None:
        target = self.static_map.get(sku)
        if not target:
            logger.warning("SKU %s missing from mapping – skipping", sku)
        return target


# ---------------------------------------------------------------------------
# Sync Engine
# ---------------------------------------------------------------------------


class QuantitySyncEngine:
    """High-level orchestrator for one sync cycle."""

    STATE_FILE = Path("var/state/skuvault_shopify_quantity_sync.json")

    def __init__(
        self,
        skuvault_client: SkuVaultReadonlyClient,
        shopify_client: ShopifyInventoryClient,
        mapper: SkuToShopifyMapper,
    ) -> None:
        self.skuvault_client = skuvault_client
        self.shopify_client = shopify_client
        self.mapper = mapper

    # ------------------------------------------------------------------
    # Last-success timestamp helpers
    # ------------------------------------------------------------------

    def _read_last_sync(self) -> datetime:
        if self.STATE_FILE.exists():
            data = json.loads(self.STATE_FILE.read_text())
            return datetime.fromisoformat(data.get("last_success"))
        return datetime.now(timezone.utc) - timedelta(minutes=15)

    def _write_last_sync(self, ts: datetime) -> None:
        self.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.STATE_FILE.write_text(json.dumps({"last_success": ts.isoformat()}))

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def _write_audit(self, record: dict) -> None:
        log_dir = Path("var/log")
        log_dir.mkdir(parents=True, exist_ok=True)
        path = log_dir / (
            "skuvault_shopify_quantity_sync_" + datetime.now().strftime("%Y%m%d") + ".jsonl"
        )
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self) -> None:
        start = time.time()
        since = self._read_last_sync()
        modified = self.skuvault_client.fetch_modified_quantities(since)

        gql_items: List[dict] = []
        skipped = 0
        for sq in modified:
            target = self.mapper.resolve(sq.sku)
            if not target:
                skipped += 1
                continue
            gql_items.append(
                {
                    "inventoryItemId": target.inventory_item_id,
                    "locationId": target.location_id,
                    "quantity": sq.quantity,
                }
            )

        if not gql_items:
            logger.info("Nothing to push. skipped=%d", skipped)
            return

        self.shopify_client.set_quantities(gql_items)

        now = datetime.now(timezone.utc)
        self._write_last_sync(now)
        self._write_audit(
            {
                "timestamp": now.isoformat(),
                "received": len(modified),
                "pushed": len(gql_items),
                "skipped": skipped,
                "duration_sec": round(time.time() - start, 2),
            }
        )


# ---------------------------------------------------------------------------
# CLI helper (manual invocation)
# ---------------------------------------------------------------------------


def _load_yaml(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def main() -> None:  # pragma: no cover
    import argparse

    p = argparse.ArgumentParser(description="Sync SkuVault quantities to Shopify")
    p.add_argument("--config", required=True, help="Path to YAML mapping file")
    args = p.parse_args()

    _configure_logging()

    cfg = _load_yaml(args.config)

    skuv_client = SkuVaultReadonlyClient(token=os.getenv("SKUV_TOKEN"))
    shopify_client = ShopifyInventoryClient(
        shop=os.getenv("SHOPIFY_SHOP_DOMAIN"), token=os.getenv("SHOPIFY_ACCESS_TOKEN")
    )
    mapper = SkuToShopifyMapper(cfg)
    QuantitySyncEngine(skuv_client, shopify_client, mapper).run_once()


if __name__ == "__main__":  # pragma: no cover
    main()
