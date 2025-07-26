import sys, pathlib, json
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "python-tools"))

import pytest

from mcp_tools.skuvault.quantity_sync import (
    QuantitySyncEngine,
    SkuVaultReadonlyClient,
    ShopifyInventoryClient,
    SkuToShopifyMapper,
    SyncError,
)


class DummyResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


@pytest.fixture
def mapping_cfg():
    return {
        "sku_mapping": [
            {
                "skuvault_sku": "SV-A",
                "shopify_inventory_item_id": "gid://shopify/InventoryItem/111",
                "location_id": "gid://shopify/Location/1001",
            },
            {
                "skuvault_sku": "SV-B",
                "shopify_inventory_item_id": "gid://shopify/InventoryItem/222",
                "location_id": "gid://shopify/Location/1001",
            },
        ]
    }


def test_happy_path(monkeypatch, tmp_path, mapping_cfg, caplog):
    def fake_post_skuv(url, json=None, timeout=None):  # noqa: A002
        return DummyResponse(
            200,
            {"Items": [
                {"Sku": "SV-A", "QuantityOnHand": 5},
                {"Sku": "SV-B", "QuantityOnHand": 9},
            ]},
        )

    # Clients
    sk_client = SkuVaultReadonlyClient(token="x")
    monkeypatch.setattr(sk_client.session, "post", fake_post_skuv, raising=True)

    captured = {}

    def fake_post_shopify(url, json=None, timeout=None):  # noqa: A002
        captured["payload"] = json
        return DummyResponse(200, {"data": {"inventorySetOnHandQuantities": {"userErrors": []}}})

    sh_client = ShopifyInventoryClient(shop="example.myshopify.com", token="y")
    monkeypatch.setattr(sh_client.session, "post", fake_post_shopify, raising=True)

    engine = QuantitySyncEngine(sk_client, sh_client, SkuToShopifyMapper(mapping_cfg))
    engine.STATE_FILE = tmp_path / "state.json"

    caplog.set_level("INFO")
    engine.run_once()

    set_qty = captured["payload"]["variables"]["input"]["setQuantities"]
    assert {q["inventoryItemId"] for q in set_qty} == {
        "gid://shopify/InventoryItem/111",
        "gid://shopify/InventoryItem/222",
    }

    assert {q["quantity"] for q in set_qty} == {5, 9}
    assert engine.STATE_FILE.exists()
    assert any("Shopify update successful" in r.message for r in caplog.records)


def test_shopify_error(monkeypatch, mapping_cfg):
    def fake_post_skuv(url, json=None, timeout=None):  # noqa: A002
        return DummyResponse(200, {"Items": [{"Sku": "SV-A", "QuantityOnHand": 1}]})

    def fake_post_shopify(url, json=None, timeout=None):  # noqa: A002
        return DummyResponse(
            200,
            {
                "data": {
                    "inventorySetOnHandQuantities": {
                        "userErrors": [
                            {"field": ["setQuantities"], "code": "INVALID", "message": "Boom"}
                        ]
                    }
                }
            },
        )

    sk_client = SkuVaultReadonlyClient(token="t1")
    monkeypatch.setattr(sk_client.session, "post", fake_post_skuv, raising=True)

    sh_client = ShopifyInventoryClient(shop="myshop.myshopify.com", token="t2")
    monkeypatch.setattr(sh_client.session, "post", fake_post_shopify, raising=True)

    engine = QuantitySyncEngine(sk_client, sh_client, SkuToShopifyMapper(mapping_cfg))

    with pytest.raises(SyncError):
        engine.run_once()
