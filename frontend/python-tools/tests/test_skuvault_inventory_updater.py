import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "python-tools"))

import builtins
from pathlib import Path
import json
import types
import pytest
from mcp_tools.skuvault.inventory_updater import (
    InventoryUpdater,
    SkuVaultClient,
    ConfigError,
    SkuVaultError,
    UpsertPayloadItem,
)


class DummyResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


def make_temp_config(tmp_path):
    cfg = {
        'sku_mapping': [
            {
                'shopify_sku': 'A',
                'skuvault_sku': 'SV-A',
                'warehouse_id': 'W1',
                'oversell_buffer': 2,
            },
            {
                'shopify_sku': 'B',
                'skuvault_sku': 'SV-B',
                'warehouse_id': 'W1',
                'locked': True,
            },
        ]
    }
    path = tmp_path / 'cfg.yaml'
    path.write_text(json.dumps(cfg))  # using json for simplicity – parser can read too
    return path, cfg


def test_single_update_applies_business_rules(monkeypatch, tmp_path, caplog):
    path, cfg_dict = make_temp_config(tmp_path)

    # Patch requests.Session.post to capture payload
    captured = {}

    def fake_post(self, url, json=None, timeout=None):  # noqa: A002
        captured['url'] = url
        captured['json'] = json
        return DummyResponse(200, {'Success': True})

    monkeypatch.setattr('requests.Session.post', fake_post, raising=True)

    client = SkuVaultClient(token='dummy')
    updater = InventoryUpdater(cfg_dict, client)

    caplog.set_level('INFO')
    updater.process_single('A', 10)

    # Verify oversell buffer applied (10 - 2) = 8
    assert captured['json']['Quantities'][0]['Quantity'] == 8
    assert captured['json']['Quantities'][0]['Sku'] == 'SV-A'

    # Locked SKU should be skipped – no additional calls
    updater.process_single('B', 5)
    # Only first call capture; process_single('B') returns None, no change
    assert captured['json']['Quantities'][0]['Sku'] == 'SV-A'

    # Verify logs
    messages = [rec.message for rec in caplog.records]
    assert any('SKU locked' in m for m in messages)


def test_batch_update_skips_unmapped(monkeypatch, tmp_path):
    path, cfg_dict = make_temp_config(tmp_path)

    captured = {}

    def fake_post(self, url, json=None, timeout=None):  # noqa: A002
        captured['json'] = json
        return DummyResponse(200, {'Success': True})

    monkeypatch.setattr('requests.Session.post', fake_post, raising=True)

    updater = InventoryUpdater(cfg_dict, SkuVaultClient('dummy'))
    updates = {'A': 10, 'C': 5}
    updater.process_batch(updates)

    assert len(captured['json']['Quantities']) == 1  # Only A sent
    assert captured['json']['Quantities'][0]['Sku'] == 'SV-A'


def test_missing_config_file(tmp_path):
    with pytest.raises(ConfigError):
        from mcp_tools.skuvault.inventory_updater import load_config

        load_config(tmp_path / 'nope.yaml')


def test_missing_token():
    with pytest.raises(ConfigError):
        SkuVaultClient(token='')


def test_retry_backoff(monkeypatch):
    attempts = {'count': 0}

    def flaky_post(self, url, json=None, timeout=None):  # noqa: A002
        attempts['count'] += 1
        if attempts['count'] < 3:
            raise Exception('temporary network fail')
        return DummyResponse(200, {'Success': True})

    monkeypatch.setattr('requests.Session.post', flaky_post, raising=True)

    client = SkuVaultClient('dummy')
    payload = [UpsertPayloadItem('SV-A', 1, 'W1')]

    resp = client.update_quantities(payload)
    assert resp['Success'] is True
    assert attempts['count'] == 3  # two fails + one success


def test_api_error(monkeypatch):
    def unauth_post(self, url, json=None, timeout=None):  # noqa: A002
        return DummyResponse(401, {'Message': 'Unauthorized'})

    monkeypatch.setattr('requests.Session.post', unauth_post, raising=True)

    client = SkuVaultClient('dummy')
    with pytest.raises(SkuVaultError):
        client.update_quantities([UpsertPayloadItem('SV-A', 1, 'W1')])
