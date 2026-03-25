from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "opinion_mcp" / "services" / "api_key_registry.py"


def _load_registry_module():
    spec = importlib.util.spec_from_file_location(
        "test_api_key_registry_module", REGISTRY_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_api_key_registry_create_lookup_revoke_cycle(tmp_path):
    module = _load_registry_module()
    registry = module.ApiKeyRegistry(storage_path=tmp_path / "api_keys.json")

    record = registry.create_key(account_id="acct-a", note="alpha")

    assert record["account_id"] == "acct-a"
    assert record["status"] == "active"
    assert registry.resolve_account_id(record["api_key"]) == "acct-a"

    assert registry.revoke_key(record["api_key"]) is True
    assert registry.resolve_account_id(record["api_key"]) is None


def test_api_key_registry_lists_metadata_without_leaking_revoked_status(tmp_path):
    module = _load_registry_module()
    registry = module.ApiKeyRegistry(storage_path=tmp_path / "api_keys.json")

    active = registry.create_key(account_id="acct-a", note="alpha")
    revoked = registry.create_key(account_id="acct-b", note="beta")
    registry.revoke_key(revoked["api_key"])

    rows = registry.list_keys()

    assert [row["account_id"] for row in rows] == ["acct-a", "acct-b"]
    assert rows[0]["status"] == "active"
    assert rows[1]["status"] == "revoked"
