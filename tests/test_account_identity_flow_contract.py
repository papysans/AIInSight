from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_CONTEXT_PATH = ROOT / "opinion_mcp" / "services" / "account_context.py"
PUBLISH_PATH = ROOT / "opinion_mcp" / "tools" / "publish.py"
SETTINGS_PATH = ROOT / "opinion_mcp" / "tools" / "settings.py"
BACKEND_CLIENT_PATH = ROOT / "opinion_mcp" / "services" / "backend_client.py"


def _stub_logger():
    loguru_stub = types.ModuleType("loguru")
    setattr(
        loguru_stub,
        "logger",
        types.SimpleNamespace(
            info=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            debug=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        ),
    )
    sys.modules["loguru"] = loguru_stub


def _load_account_context_module():
    spec = importlib.util.spec_from_file_location(
        "test_account_context_module", ACCOUNT_CONTEXT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_publish_module():
    _stub_logger()
    account_context = _load_account_context_module()
    sys.modules["opinion_mcp.services.account_context"] = account_context

    backend_client_stub = types.ModuleType("opinion_mcp.services.backend_client")
    backend_client_stub.backend_client = types.SimpleNamespace(
        publish_xhs=None,
        get_xhs_status=None,
        get_xhs_login_qrcode=None,
        reset_xhs_login=None,
        submit_xhs_verification=None,
        check_xhs_login_session=None,
    )
    sys.modules["opinion_mcp.services.backend_client"] = backend_client_stub

    job_manager_stub = types.ModuleType("opinion_mcp.services.job_manager")
    job_manager_stub.job_manager = types.SimpleNamespace(get_job=None)
    sys.modules["opinion_mcp.services.job_manager"] = job_manager_stub

    url_validator_stub = types.ModuleType("opinion_mcp.utils.url_validator")
    url_validator_stub.filter_valid_urls = lambda *args, **kwargs: []
    url_validator_stub.download_images = None
    sys.modules["opinion_mcp.utils.url_validator"] = url_validator_stub

    spec = importlib.util.spec_from_file_location("test_publish_module", PUBLISH_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, account_context


def _load_settings_module():
    _stub_logger()
    account_context = _load_account_context_module()
    sys.modules["opinion_mcp.services.account_context"] = account_context

    config_stub = types.ModuleType("opinion_mcp.config")
    config_stub.config = types.SimpleNamespace(
        AVAILABLE_SOURCES=[],
        DEFAULT_SOURCE_GROUPS=["media"],
        SOURCE_GROUPS={"media": ["hn"]},
        DEPTH_PRESETS={"standard": {}},
        DEFAULT_IMAGE_COUNT=0,
        DEFAULT_DEBATE_ROUNDS=2,
    )
    sys.modules["opinion_mcp.config"] = config_stub

    job_manager_stub = types.ModuleType("opinion_mcp.services.job_manager")
    job_manager_stub.job_manager = types.SimpleNamespace(
        get_job=None, set_webhook_url=None
    )
    sys.modules["opinion_mcp.services.job_manager"] = job_manager_stub

    webhook_manager_stub = types.ModuleType("opinion_mcp.services.webhook_manager")
    webhook_manager_stub.webhook_manager = types.SimpleNamespace(register=None)
    sys.modules["opinion_mcp.services.webhook_manager"] = webhook_manager_stub

    spec = importlib.util.spec_from_file_location("test_settings_module", SETTINGS_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, account_context


def _load_backend_client_module():
    _stub_logger()
    config_stub = types.ModuleType("opinion_mcp.config")
    config_stub.config = types.SimpleNamespace(
        BACKEND_URL="http://localhost:8000", REQUEST_TIMEOUT=300
    )
    sys.modules["opinion_mcp.config"] = config_stub

    spec = importlib.util.spec_from_file_location(
        "test_backend_client_identity_module", BACKEND_CLIENT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_publish_tool_uses_account_context_for_job_lookup(monkeypatch):
    module, account_context = _load_publish_module()
    account_context.set_account_id("acct-a")

    captured = {}

    class FakeJob:
        published = False
        is_running = False
        is_failed = False
        result = types.SimpleNamespace(
            copywriting=types.SimpleNamespace(title="T", content="C", tags=[]),
            ai_images=[],
            cards=None,
        )

    async def fake_collect_images_for_publish(result, mode):
        return [], []

    def fake_get_job(job_id, account_id=None):
        captured["account_id"] = account_id
        return FakeJob()

    monkeypatch.setattr(
        module, "collect_images_for_publish", fake_collect_images_for_publish
    )
    monkeypatch.setattr(module.job_manager, "get_job", fake_get_job)

    await module.publish_to_xhs(job_id="job_1")

    assert captured["account_id"] == "acct-a"


@pytest.mark.asyncio
async def test_register_webhook_uses_account_context(monkeypatch):
    module, account_context = _load_settings_module()
    account_context.set_account_id("acct-b")
    captured = {}

    class FakeJob:
        is_completed = False
        is_failed = False

    def fake_get_job(job_id, account_id=None):
        captured["lookup_account"] = account_id
        return FakeJob()

    def fake_register(job_id, callback_url, account_id=None):
        captured["register_account"] = account_id
        return True

    def fake_set_webhook_url(job_id, callback_url, account_id=None):
        captured["set_account"] = account_id
        return True

    monkeypatch.setattr(module.job_manager, "get_job", fake_get_job)
    monkeypatch.setattr(module.job_manager, "set_webhook_url", fake_set_webhook_url)
    monkeypatch.setattr(module.webhook_manager, "register", fake_register)

    result = await module.register_webhook("https://example.com/hook", "job_1")

    assert result["success"] is True
    assert captured == {
        "lookup_account": "acct-b",
        "register_account": "acct-b",
        "set_account": "acct-b",
    }


@pytest.mark.asyncio
async def test_backend_client_forwards_account_header(monkeypatch):
    module = _load_backend_client_module()
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"ok": True}

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            calls.append((url, headers))
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)

    client = module.BackendClient("http://localhost:8000")
    await client.retrieve_and_report(topic="AI Infra", account_id="acct-c")

    assert calls == [
        (
            "http://localhost:8000/api/retrieve-and-report",
            {"Content-Type": "application/json", "X-Account-Id": "acct-c"},
        )
    ]
