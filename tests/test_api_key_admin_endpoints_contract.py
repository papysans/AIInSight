from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "opinion_mcp" / "server.py"


def _stub_module(name: str, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _load_server_module():
    _stub_module(
        "loguru",
        logger=types.SimpleNamespace(
            info=lambda *a, **k: None,
            error=lambda *a, **k: None,
            warning=lambda *a, **k: None,
            debug=lambda *a, **k: None,
            exception=lambda *a, **k: None,
            remove=lambda *a, **k: None,
            add=lambda *a, **k: None,
        ),
    )

    class _FastAPI:
        def __init__(self, *args, **kwargs):
            pass

        def add_middleware(self, *args, **kwargs):
            return None

        def middleware(self, *args, **kwargs):
            return lambda fn: fn

        def get(self, *args, **kwargs):
            return lambda fn: fn

        def post(self, *args, **kwargs):
            return lambda fn: fn

    class _HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail

    class _Request:
        def __init__(self, headers=None):
            self.headers = headers or {}

    _stub_module(
        "fastapi", FastAPI=_FastAPI, HTTPException=_HTTPException, Request=_Request
    )
    _stub_module("fastapi.middleware.cors", CORSMiddleware=object)
    _stub_module("fastapi.responses", StreamingResponse=object)
    _stub_module("uvicorn", run=lambda *args, **kwargs: None)

    class _BaseModel:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

        def model_dump(self):
            return self.__dict__

    def _field(default=None, default_factory=None, **kwargs):
        if default_factory is not None:
            return default_factory()
        return default

    _stub_module("pydantic", BaseModel=_BaseModel, Field=_field)

    _stub_module(
        "opinion_mcp.config",
        config=types.SimpleNamespace(
            BACKEND_URL="http://localhost:8000",
            MCP_PORT=18061,
            MCP_HOST="localhost",
            REQUIRE_API_KEY=False,
        ),
    )

    _stub_module(
        "opinion_mcp.services.api_key_registry",
        api_key_registry=types.SimpleNamespace(
            resolve_account_id=lambda api_key: None,
            create_key=None,
            list_keys=None,
            revoke_key=None,
        ),
    )

    account_context_mod = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location(
            "opinion_mcp.services.account_context",
            ROOT / "opinion_mcp" / "services" / "account_context.py",
        )
    )
    account_context_mod.__spec__.loader.exec_module(account_context_mod)
    sys.modules["opinion_mcp.services.account_context"] = account_context_mod

    async def _noop_async(**kwargs):
        return kwargs

    _stub_module(
        "opinion_mcp.tools",
        analyze_topic=_noop_async,
        retrieve_and_report=_noop_async,
        submit_analysis_result=_noop_async,
        get_analysis_status=_noop_async,
        get_analysis_result=_noop_async,
        update_copywriting=_noop_async,
        generate_topic_cards=_noop_async,
        get_xhs_login_qrcode=_noop_async,
        check_xhs_status=_noop_async,
        xhs_login=_noop_async,
        reset_xhs_login=_noop_async,
        submit_xhs_verification=_noop_async,
        check_xhs_login_session=_noop_async,
        upload_xhs_cookies=_noop_async,
        get_xhs_login_qrcode_v2=_noop_async,
        poll_xhs_login_v2=_noop_async,
        publish_to_xhs=_noop_async,
        get_settings=_noop_async,
        register_webhook=_noop_async,
        get_ai_daily=_noop_async,
        analyze_ai_topic=_noop_async,
        generate_ai_daily_cards=_noop_async,
        publish_ai_daily=_noop_async,
        generate_ai_daily_ranking_cards=_noop_async,
        publish_ai_daily_ranking=_noop_async,
    )
    _stub_module("opinion_mcp.tools.validate_publish", validate_publish=_noop_async)

    spec = importlib.util.spec_from_file_location(
        "test_api_key_admin_server", SERVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_create_api_key_endpoint_delegates_to_registry(monkeypatch):
    module = _load_server_module()

    captured = {}

    def fake_create_key(account_id: str, note: str = ""):
        captured.update({"account_id": account_id, "note": note})
        return {
            "api_key": "k1",
            "account_id": account_id,
            "note": note,
            "status": "active",
        }

    monkeypatch.setattr(module.api_key_registry, "create_key", fake_create_key)

    body = module.ApiKeyCreateRequest(account_id="acct-a", note="alpha")
    result = await module.create_api_key(body)

    assert captured == {"account_id": "acct-a", "note": "alpha"}
    assert result["api_key"] == "k1"


@pytest.mark.asyncio
async def test_list_api_keys_endpoint_returns_registry_rows(monkeypatch):
    module = _load_server_module()

    monkeypatch.setattr(
        module.api_key_registry,
        "list_keys",
        lambda: [{"account_id": "acct-a", "note": "alpha", "status": "active"}],
    )

    result = await module.list_api_keys()

    assert result == {
        "success": True,
        "keys": [{"account_id": "acct-a", "note": "alpha", "status": "active"}],
    }


@pytest.mark.asyncio
async def test_revoke_api_key_endpoint_delegates_to_registry(monkeypatch):
    module = _load_server_module()

    monkeypatch.setattr(
        module.api_key_registry, "revoke_key", lambda api_key: api_key == "k1"
    )

    ok = await module.revoke_api_key(module.ApiKeyRevokeRequest(api_key="k1"))
    assert ok == {"success": True, "revoked": True}

    bad = await module.revoke_api_key(module.ApiKeyRevokeRequest(api_key="missing"))
    assert bad == {"success": False, "revoked": False}
