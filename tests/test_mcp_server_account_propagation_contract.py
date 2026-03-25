from __future__ import annotations

import importlib.util
import json
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
        def __init__(self, headers=None, json_body=None):
            self.headers = headers or {}
            self._json_body = json_body

        async def json(self):
            return self._json_body

    _stub_module(
        "fastapi", FastAPI=_FastAPI, HTTPException=_HTTPException, Request=_Request
    )
    _stub_module("fastapi.middleware.cors", CORSMiddleware=object)
    _stub_module("fastapi.responses", StreamingResponse=object)
    _stub_module("uvicorn", run=lambda *args, **kwargs: None)

    class _BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

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
            BACKEND_URL="http://localhost:8000", MCP_PORT=18061, MCP_HOST="localhost"
        ),
    )

    _stub_module(
        "opinion_mcp.services.api_key_registry",
        api_key_registry=types.SimpleNamespace(
            resolve_account_id=lambda api_key: {"acct-key": "acct-resolved"}.get(
                api_key
            )
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
        "test_server_account_module", SERVER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_handle_jsonrpc_request_injects_account_from_context(monkeypatch):
    module = _load_server_module()

    captured = {}

    async def fake_handler(**kwargs):
        captured.update(kwargs)
        return {"success": True}

    module.TOOL_HANDLERS["retrieve_and_report"] = fake_handler
    module.set_account_id("acct-jsonrpc")

    response = await module.handle_jsonrpc_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "retrieve_and_report",
                "arguments": {"topic": "AI Infra"},
            },
        }
    )

    assert captured["topic"] == "AI Infra"
    assert captured["account_id"] == "acct-jsonrpc"
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_direct_http_wrappers_forward_account_id_from_body():
    module = _load_server_module()
    captured = {}

    async def fake_analyze_topic(**kwargs):
        captured.update(kwargs)
        return {"success": True}

    module.analyze_topic = fake_analyze_topic

    body = module.AnalyzeTopicRequest(
        topic="AI Infra",
        source_groups=["media"],
        source_names=None,
        depth="standard",
        debate_rounds=2,
        image_count=0,
        account_id="acct-http",
    )

    await module.direct_analyze_topic_post(body)

    assert captured["account_id"] == "acct-http"
    assert captured["topic"] == "AI Infra"


@pytest.mark.asyncio
async def test_http_mcp_call_tool_injects_account_from_request_body_context():
    module = _load_server_module()
    captured = {}

    async def fake_handler(**kwargs):
        captured.update(kwargs)
        return {"success": True}

    module.TOOL_HANDLERS["retrieve_and_report"] = fake_handler
    module.set_account_id("acct-http-mcp")

    request = module.MCPCallToolRequest(
        name="retrieve_and_report",
        arguments={"topic": "AI Infra"},
    )

    response = await module.mcp_call_tool(request)

    assert captured["account_id"] == "acct-http-mcp"
    assert captured["topic"] == "AI Infra"
    assert response.isError is False


def test_resolve_account_id_prefers_api_key_then_forwarded_header():
    module = _load_server_module()

    request_with_key = module.Request(headers={"X-API-Key": "acct-key"})
    request_with_forwarded = module.Request(headers={"X-Account-Id": "acct-forwarded"})
    request_empty = module.Request(headers={})

    assert module._resolve_account_id_from_request(request_with_key) == "acct-resolved"
    assert (
        module._resolve_account_id_from_request(request_with_forwarded)
        == "acct-forwarded"
    )
    assert module._resolve_account_id_from_request(request_empty) == "_default"


def test_require_api_key_rejects_missing_or_unknown_key():
    module = _load_server_module()
    module.config.REQUIRE_API_KEY = True

    request_missing = module.Request(headers={})
    request_invalid = module.Request(headers={"X-API-Key": "unknown"})
    request_valid = module.Request(headers={"X-API-Key": "acct-key"})

    missing_error = module._validate_or_resolve_account_id(request_missing)
    invalid_error = module._validate_or_resolve_account_id(request_invalid)
    valid_account = module._validate_or_resolve_account_id(request_valid)

    assert isinstance(missing_error, module.HTTPException)
    assert missing_error.status_code == 401
    assert isinstance(invalid_error, module.HTTPException)
    assert invalid_error.status_code == 401
    assert valid_account == "acct-resolved"
