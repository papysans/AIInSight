from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
BACKEND_CLIENT_PATH = ROOT / "opinion_mcp" / "services" / "backend_client.py"
ANALYZE_PATH = ROOT / "opinion_mcp" / "tools" / "analyze.py"
SERVER_PATH = ROOT / "opinion_mcp" / "server.py"
TOOLS_INIT_PATH = ROOT / "opinion_mcp" / "tools" / "__init__.py"


def _load_backend_client_module():
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

    config_stub = types.ModuleType("opinion_mcp.config")
    setattr(
        config_stub,
        "config",
        types.SimpleNamespace(BACKEND_URL="http://localhost:8000", REQUEST_TIMEOUT=300),
    )
    sys.modules["opinion_mcp.config"] = config_stub

    account_context_stub = types.ModuleType("opinion_mcp.services.account_context")
    account_context_stub.get_account_id = lambda: "_default"
    sys.modules["opinion_mcp.services.account_context"] = account_context_stub

    spec = importlib.util.spec_from_file_location(
        "test_backend_client_split_module", BACKEND_CLIENT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_analyze_module():
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

    config_stub = types.ModuleType("opinion_mcp.config")
    setattr(
        config_stub,
        "config",
        types.SimpleNamespace(
            DEPTH_PRESETS={"standard": {"debate_rounds": 2}},
            MAX_DEBATE_ROUNDS=5,
            MAX_IMAGE_COUNT=9,
            DEFAULT_SOURCE_GROUPS=["media"],
            SOURCE_GROUPS={"media": ["hn"]},
        ),
    )
    sys.modules["opinion_mcp.config"] = config_stub

    schemas_stub = types.ModuleType("opinion_mcp.schemas")
    for name in [
        "JobStatus",
        "EventType",
        "AnalyzeTopicResponse",
        "AnalysisStatusResponse",
        "AnalysisResultResponse",
        "Copywriting",
        "AnalysisCards",
        "WebhookData",
    ]:
        setattr(schemas_stub, name, type(name, (), {}))
    sys.modules["opinion_mcp.schemas"] = schemas_stub

    backend_client_stub = types.ModuleType("opinion_mcp.services.backend_client")
    backend_client_stub.backend_client = types.SimpleNamespace(
        retrieve_and_report=None,
        submit_analysis_result=None,
        call_analyze_api=None,
    )
    sys.modules["opinion_mcp.services.backend_client"] = backend_client_stub

    job_manager_stub = types.ModuleType("opinion_mcp.services.job_manager")
    job_manager_stub.job_manager = types.SimpleNamespace(
        get_current_job=lambda: None,
        create_job=lambda **kwargs: "job_123",
        update_status=lambda *args, **kwargs: None,
    )
    sys.modules["opinion_mcp.services.job_manager"] = job_manager_stub

    webhook_manager_stub = types.ModuleType("opinion_mcp.services.webhook_manager")
    webhook_manager_stub.webhook_manager = types.SimpleNamespace(push_started=None)
    sys.modules["opinion_mcp.services.webhook_manager"] = webhook_manager_stub

    spec = importlib.util.spec_from_file_location(
        "test_analyze_split_module", ANALYZE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_backend_client_posts_retrieve_and_report_contract(monkeypatch):
    module = _load_backend_client_module()
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "topic": "AI Infra",
                "evidence_bundle": {"items": [{"id": "e1"}]},
                "source_stats": {"hn": 2},
                "news_content": "cloud-side summary",
            }

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            calls.append((url, json, headers, self.timeout))
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)

    client = module.BackendClient("http://localhost:8000")
    result = await client.retrieve_and_report(
        topic="AI Infra",
        source_groups=["media"],
        source_names=None,
        depth="standard",
    )

    assert calls == [
        (
            "http://localhost:8000/api/retrieve-and-report",
            {
                "topic": "AI Infra",
                "depth": "standard",
                "source_groups": ["media"],
            },
            {"Content-Type": "application/json"},
            300,
        )
    ]
    assert result["news_content"] == "cloud-side summary"


@pytest.mark.asyncio
async def test_backend_client_posts_submit_analysis_result_contract(monkeypatch):
    module = _load_backend_client_module()
    calls = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "topic": "AI Infra",
                "final_copy": "TITLE: demo\nCONTENT:\nbody",
                "image_urls": ["https://img.example/1.png"],
            }

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json=None, headers=None):
            calls.append((url, json, headers, self.timeout))
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)

    client = module.BackendClient("http://localhost:8000")
    result = await client.submit_analysis_result(
        topic="AI Infra",
        news_content="cloud-side summary",
        final_analysis="host debate final analysis",
        debate_history=["Analyst round 1", "Debater round 1"],
        source_stats={"hn": 2},
        image_count=1,
    )

    assert calls == [
        (
            "http://localhost:8000/api/submit-analysis-result",
            {
                "topic": "AI Infra",
                "news_content": "cloud-side summary",
                "final_analysis": "host debate final analysis",
                "debate_history": ["Analyst round 1", "Debater round 1"],
                "source_stats": {"hn": 2},
                "image_count": 1,
                "xhs_publish_enabled": False,
            },
            {"Content-Type": "application/json"},
            300,
        )
    ]
    assert result["final_copy"] == "TITLE: demo\nCONTENT:\nbody"


@pytest.mark.asyncio
async def test_analyze_module_exposes_split_tool_wrappers(monkeypatch):
    module = _load_analyze_module()

    async def fake_retrieve_and_report(**kwargs):
        assert kwargs == {
            "topic": "AI Infra",
            "source_groups": ["media"],
            "source_names": None,
            "depth": "standard",
            "account_id": "_default",
        }
        return {"news_content": "cloud-side summary"}

    async def fake_submit_analysis_result(**kwargs):
        assert kwargs["final_analysis"] == "host debate final analysis"
        return {"final_copy": "TITLE: demo\nCONTENT:\nbody"}

    monkeypatch.setattr(
        module.backend_client, "retrieve_and_report", fake_retrieve_and_report
    )
    monkeypatch.setattr(
        module.backend_client, "submit_analysis_result", fake_submit_analysis_result
    )

    front = await module.retrieve_and_report(
        topic="AI Infra",
        source_groups=["media"],
        source_names=None,
        depth="standard",
    )
    back = await module.submit_analysis_result(
        topic="AI Infra",
        news_content="cloud-side summary",
        final_analysis="host debate final analysis",
        debate_history=["Analyst round 1"],
        source_stats={"hn": 2},
        image_count=1,
    )

    assert front == {"news_content": "cloud-side summary"}
    assert back == {"final_copy": "TITLE: demo\nCONTENT:\nbody"}


def test_mcp_server_registers_split_tools():
    server_source = SERVER_PATH.read_text(encoding="utf-8")
    tools_source = TOOLS_INIT_PATH.read_text(encoding="utf-8")

    assert 'name="retrieve_and_report"' in server_source
    assert 'name="submit_analysis_result"' in server_source
    assert '"retrieve_and_report": retrieve_and_report' in server_source
    assert '"submit_analysis_result": submit_analysis_result' in server_source
    assert "retrieve_and_report" in tools_source
    assert "submit_analysis_result" in tools_source
