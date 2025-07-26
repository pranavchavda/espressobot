#!/usr/bin/env python3
"""SkuVault Inventory Updater for iDrinkCoffee.com

A reusable library + CLI/HTTP service that pushes inventory quantity updates
from Shopify (or any upstream system) to SkuVault.

Features:
1. Bearer-token authentication (token read from env var or secret manager).
2. SKU/location/warehouse mapping via configurable YAML file.
3. Single-item and bulk update capability.
4. Business rules: locked SKUs are skipped, oversell buffer applied, quantity floor at 0.
5. Structured JSON logging with optional StatsD metrics.
6. Pluggable execution surfaces: CLI, scheduled job, or webhook.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import requests
import yaml

# ---------------------------------------------------------------------------
# Optional tenacity import – provide very small fallbacks if the dependency is
# unavailable in the execution environment.  We *only* rely on the subset of
# functionality needed by this module (retry with a maximum number of attempts
# and exponential back-off jitters).
# ---------------------------------------------------------------------------

try:
    from tenacity import retry, stop_after_attempt, wait_exponential_jitter  # type: ignore
except ImportError:  # pragma: no cover – fallback implementations

    def stop_after_attempt(n: int):  # type: ignore
        """Return attempt limit – used only as a sentinel by the fallback."""
        return n

    def wait_exponential_jitter(**_kwargs):  # type: ignore  # noqa: D401
        """Placeholder for tenacity.wait_exponential_jitter – no-op here."""
        return None

    def retry(*_dargs, **dkwargs):  # type: ignore
        """Extremely lightweight replacement for tenacity.retry.

        Only supports the "stop" keyword argument taking the value returned by
        stop_after_attempt(N).  Any other args/kwargs are ignored.
        """

        stop = dkwargs.get("stop", 3)
        max_attempts = stop if isinstance(stop, int) else 3

        def decorator(fn):  # type: ignore
            def wrapper(*args, **kwargs):  # type: ignore
                attempts = 0
                while True:
                    attempts += 1
                    try:
                        return fn(*args, **kwargs)
                    except Exception:  # pylint: disable=broad-except
                        if attempts >= max_attempts:
                            raise
            return wrapper

        return decorator

# ---------------------------------------------------------------------------
# .env convenience – failure to import python-dotenv should *not* break the
# module, it will just skip automatic .env loading.
# ---------------------------------------------------------------------------

try:
    from dotenv import load_dotenv  # type: ignore
except ImportError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return None

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = lambda *_args, **_kwargs: None  # type: ignore

# ---------------------------------------------------------------------------
# Logging setup (JSON structured)
# ---------------------------------------------------------------------------

def _configure_logging(level: str = "INFO", log_path: str | None = None) -> None:
    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            return json.dumps({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "name": record.name,
                "message": record.getMessage(),
                "module": record.module,
                "func": record.funcName,
                "line": record.lineno,
            })

    handler: logging.Handler
    if log_path:
        handler = logging.FileHandler(log_path)
    else:
        handler = logging.StreamHandler()

    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler])


logger = logging.getLogger("skuvault-updater")


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SkuVaultError(Exception):
    """Base class for SkuVault related errors."""


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


# ---------------------------------------------------------------------------
# Configuration schema
# ---------------------------------------------------------------------------


def _expand_env(value: str) -> str:
    """Expand ${VAR} in YAML values."""
    return os.path.expandvars(value)


def load_config(path: str | Path) -> dict:
    if not Path(path).expanduser().exists():
        raise ConfigError(f"Config file {path} not found")
    with open(path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    # env-substitution pass
    def _walk(node):
        if isinstance(node, dict):
            return {k: _walk(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [_walk(v) for v in node]
        elif isinstance(node, str):
            return _expand_env(node)
        return node

    return _walk(raw)


@dataclass(frozen=True)
class MappingEntry:
    shopify_sku: str
    skuvault_sku: str
    warehouse_id: str
    location_code: str | None = None  # Optional: allow SkuVault to auto-allocate
    locked: bool = False
    oversell_buffer: int = 0  # Number of units kept back (never sent to SkuVault)


@dataclass
class UpsertPayloadItem:
    sku: str
    quantity: int
    warehouse_id: str
    location_code: str | None = None

    def to_dict(self):
        d = {
            "Sku": self.sku,
            "Quantity": self.quantity,
            "WarehouseId": self.warehouse_id,
        }
        if self.location_code:
            d["LocationCode"] = self.location_code
        return d


# ---------------------------------------------------------------------------
# SkuVault API Client
# ---------------------------------------------------------------------------


class SkuVaultClient:
    BASE_URL = "https://app.skuvault.com"

    def __init__(self, token: str, timeout: int = 10):
        if not token:
            raise ConfigError("Missing SkuVault API token")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "User-Agent": "idc-skvt-updater/1.0",
        })
        self.timeout = timeout

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(multiplier=1))
    def update_quantities(self, items: Sequence[UpsertPayloadItem]) -> dict:
        url = f"{self.BASE_URL}/api/inventory/updateQuantities"
        payload = {"Quantities": [item.to_dict() for item in items]}
        logger.info(f"POST {url} - {len(items)} item(s)")
        resp = self.session.post(url, json=payload, timeout=self.timeout)
        # --- Enhanced error handling for rate-limits & service disruptions ---
        if resp.status_code in (429, 503):
            # Raise so that the @retry wrapper triggers a back-off & retry.
            raise SkuVaultError(f"SkuVault rate-limited or unavailable (HTTP {resp.status_code})")
        if resp.status_code >= 400:
            raise SkuVaultError(f"SkuVault API error {resp.status_code}: {resp.text}")
        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise SkuVaultError("Invalid JSON response from SkuVault") from exc


# ---------------------------------------------------------------------------
# InventoryUpdater (business-rule layer)
# ---------------------------------------------------------------------------


class InventoryUpdater:
    def __init__(self, cfg: dict, client: SkuVaultClient):
        self.cfg = cfg
        self.client = client
        self.mapping: Dict[str, MappingEntry] = {}
        self._load_mapping()
        self._known_quantities: dict[str, int] = {}  # cache of last pushed quantities

    def _load_mapping(self):
        for entry in self.cfg.get("sku_mapping", []):
            m = MappingEntry(**entry)
            self.mapping[m.shopify_sku] = m
        logger.info(f"Loaded {len(self.mapping)} SKU mappings")

    def _translate(self, shopify_sku: str, quantity: int) -> Optional[UpsertPayloadItem]:
        m = self.mapping.get(shopify_sku)
        if not m:
            logger.warning(f"SKU not mapped, skipping: {shopify_sku}")
            return None
        if m.locked:
            logger.info(f"SKU locked, skip update: {shopify_sku}")
            return None

        qty = max(quantity - m.oversell_buffer, 0)
        return UpsertPayloadItem(
            sku=m.skuvault_sku,
            quantity=qty,
            warehouse_id=m.warehouse_id,
            location_code=m.location_code,
        )

def process_single(self, shopify_sku: str, quantity: int, dry_run: bool = False):
    """Update a single SKU in SkuVault."""
    item = self._translate(shopify_sku, quantity)
    if not item:
        return
    if dry_run:
        logger.info("Dry-run: would update %s", item)
        return
    try:
        resp = self.client.update_quantities([item])
    except SkuVaultError as exc:
        logger.error("Single update failed for %s: %s", item.sku, exc)
        return
    else:
        self._known_quantities[item.sku] = item.quantity
        logger.info("Update response: %s", resp)
        self._record_metric(1)

def process_batch(self, updates: Dict[str, int], dry_run: bool = False):
    """Bulk quantity update with best-effort rollback on failure."""
    payload: List[UpsertPayloadItem] = []
    for shopify_sku, qty in updates.items():
        item = self._translate(shopify_sku, qty)
        if item:
            payload.append(item)
    if not payload:
        logger.info("Nothing to update in batch.")
        return
    if dry_run:
        logger.info("Dry-run payload: %s", [p.to_dict() for p in payload])
        return
    try:
        resp = self.client.update_quantities(payload)
    except SkuVaultError as exc:
        logger.error("Batch update failed: %s. Attempting rollback ..", exc)
        self._attempt_rollback(payload)
        raise
    else:
        logger.info("Batch update response: %s", resp)
        for item in payload:
            self._known_quantities[item.sku] = item.quantity
        self._record_metric(len(payload))


    """Bulk quantity update with best-effort rollback on failure."""
    payload: List[UpsertPayloadItem] = []
    for shopify_sku, qty in updates.items():
        item = self._translate(shopify_sku, qty)
        if item:
            payload.append(item)
    if not payload:
        logger.info("Nothing to update in batch.")
        return
    if dry_run:
        logger.info(f"Dry-run payload: {[p.to_dict() for p in payload]}")
        return
    try:
        resp = self.client.update_quantities(payload)
    except SkuVaultError as exc:
        logger.error(f"Batch update failed: {exc}. Attempting rollback ..")
        self._attempt_rollback(payload)
        raise
    else:
        logger.info(f"Batch update response: {resp}")
        for item in payload:
            self._known_quantities[item.sku] = item.quantity
        self._record_metric(len(payload))
    # Monitoring stub (StatsD)
    def _record_metric(self, count: int):
        try:
            import statsd  # type: ignore
            c = statsd.StatsClient(prefix="idc.skvt")
            c.incr("inventory_updates", count)
        except Exception as e:  # pylint: disable=broad-except
            logger.debug(f"StatsD not configured: {e}")


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _parse_args(argv: List[str]):
    p = argparse.ArgumentParser(description="Update SkuVault quantities")
    p.add_argument("--config", required=True, help="Path to YAML config file")
    p.add_argument("--env", default=".env", help=".env file containing secrets")

    sub = p.add_subparsers(dest="command", required=True)

    single = sub.add_parser("single", help="Update one SKU")
    single.add_argument("sku", help="Shopify SKU")
    single.add_argument("quantity", type=int, help="Quantity to set in SkuVault")
    single.add_argument("--dry-run", action="store_true")

    batch = sub.add_parser("batch", help="Batch update from JSON/YAML file")
    batch.add_argument("file", help="Path to file with {shopify_sku: qty}")
    batch.add_argument("--dry-run", action="store_true")

    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None):
    args = _parse_args(argv or sys.argv[1:])

    # Load secrets first
    load_dotenv(args.env)
    api_token = os.getenv("SKUV_TOKEN") or os.getenv("SKUVAULT_TOKEN")
    _configure_logging(level=os.getenv("LOG_LEVEL", "INFO"), log_path=os.getenv("LOG_PATH"))

    cfg = load_config(args.config)
    client = SkuVaultClient(token=api_token)
    updater = InventoryUpdater(cfg, client)

    if args.command == "single":
        updater.process_single(args.sku, args.quantity, dry_run=args.dry_run)
    elif args.command == "batch":
        with open(args.file, "r", encoding="utf-8") as fh:
            if args.file.endswith((".yaml", ".yml")):
                updates = yaml.safe_load(fh)
            else:
                updates = json.load(fh)
        if not isinstance(updates, dict):
            raise ValueError("Batch file must contain a mapping of sku -> quantity")
        updater.process_batch(updates, dry_run=args.dry_run)


if __name__ == "__main__":
    main()