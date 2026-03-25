from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
ANALYZE_PATH = ROOT / "opinion_mcp" / "tools" / "analyze.py"


def _load_analyze_module():
    loguru_stub = types.ModuleType("loguru")
    loguru_stub.logger = types.SimpleNamespace(
        info=lambda *a, **k: None,
        error=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        debug=lambda *a, **k: None,
        exception=lambda *a, **k: None,
    )
    sys.modules["loguru"] = loguru_stub

    account_context_mod = types.ModuleType("opinion_mcp.services.account_context")
    account_context_mod.get_account_id = lambda: "acct-legacy"
    sys.modules["opinion_mcp.services.account_context"] = account_context_mod

    config_stub = types.ModuleType("opinion_mcp.config")
    config_stub.config = types.SimpleNamespace(
        DEPTH_PRESETS={"standard": {"debate_rounds": 2}},
        MAX_DEBATE_ROUNDS=5,
        MAX_IMAGE_COUNT=9,
        DEFAULT_SOURCE_GROUPS=["media"],
        SOURCE_GROUPS={"media": ["hn"]},
    )
    sys.modules["opinion_mcp.config"] = config_stub

    schemas_stub = types.ModuleType("opinion_mcp.schemas")

    class JobStatus:
        RUNNING = types.SimpleNamespace(value="running")
        COMPLETED = types.SimpleNamespace(value="completed")

    for name in [
        "AnalyzeTopicResponse",
        "AnalysisStatusResponse",
        "AnalysisResultResponse",
        "Copywriting",
        "AnalysisCards",
        "WebhookData",
        "EventType",
    ]:
        setattr(schemas_stub, name, type(name, (), {}))
    schemas_stub.JobStatus = JobStatus
    sys.modules["opinion_mcp.schemas"] = schemas_stub

    backend_client_stub = types.ModuleType("opinion_mcp.services.backend_client")
    backend_client_stub.backend_client = types.SimpleNamespace(
        call_analyze_api=None,
        retrieve_and_report=None,
        submit_analysis_result=None,
    )
    sys.modules["opinion_mcp.services.backend_client"] = backend_client_stub

    job_manager_stub = types.ModuleType("opinion_mcp.services.job_manager")
    job_manager_stub.job_manager = types.SimpleNamespace(
        get_current_job=None,
        create_job=None,
        update_status=None,
        get_job=None,
        list_jobs=None,
    )
    sys.modules["opinion_mcp.services.job_manager"] = job_manager_stub

    webhook_manager_stub = types.ModuleType("opinion_mcp.services.webhook_manager")
    webhook_manager_stub.webhook_manager = types.SimpleNamespace(
        push_started=None,
        push_failed=None,
        push_completed=None,
        push_step_change=None,
        push_platform_done=None,
        push_progress=None,
    )
    sys.modules["opinion_mcp.services.webhook_manager"] = webhook_manager_stub

    spec = importlib.util.spec_from_file_location(
        "test_legacy_analyze_module", ANALYZE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_legacy_analyze_topic_uses_context_account_for_job_creation(monkeypatch):
    module = _load_analyze_module()
    captured = {}

    monkeypatch.setattr(
        module.job_manager, "get_current_job", lambda account_id=None: None
    )

    def fake_create_job(**kwargs):
        captured.update(kwargs)
        return "job_123"

    monkeypatch.setattr(module.job_manager, "create_job", fake_create_job)
    monkeypatch.setattr(module.job_manager, "update_status", lambda *a, **k: None)

    created_tasks = []

    def fake_create_task(coro):
        created_tasks.append(coro)
        coro.close()
        return None

    monkeypatch.setattr(module.asyncio, "create_task", fake_create_task)

    result = await module.analyze_topic(topic="AI Infra", depth="standard")

    assert result["success"] is True
    assert captured["account_id"] == "acct-legacy"


@pytest.mark.asyncio
async def test_legacy_status_and_result_use_context_account(monkeypatch):
    module = _load_analyze_module()
    captured = {"get_job": [], "list_jobs": []}

    class FakeJob:
        job_id = "job_123"
        is_running = False
        current_step = None
        current_step_name = None
        progress = 100
        topic = "AI Infra"
        current_source = None
        started_at = None
        completed_at = None
        elapsed_minutes = None
        status = types.SimpleNamespace(value="completed")
        error_message = None
        result = types.SimpleNamespace(
            copywriting=None,
            cards=None,
            ai_images=[],
            summary="",
            insight="",
            sources_analyzed=[],
            skipped_sources=[],
            evidence_count=0,
            source_stats={},
            output_file=None,
        )
        is_failed = False

    def fake_get_job(job_id, account_id=None):
        captured["get_job"].append(account_id)
        return FakeJob()

    def fake_list_jobs(status=None, limit=10, account_id=None):
        captured["list_jobs"].append(account_id)
        return [FakeJob()]

    monkeypatch.setattr(module.job_manager, "get_job", fake_get_job)
    monkeypatch.setattr(module.job_manager, "list_jobs", fake_list_jobs)

    status_result = await module.get_analysis_status(job_id="job_123")
    result_result = await module.get_analysis_result()

    assert status_result["success"] is True
    assert result_result["success"] is True
    assert captured["get_job"] == ["acct-legacy"]
    assert captured["list_jobs"] == ["acct-legacy"]
