from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
JOB_MANAGER_PATH = ROOT / "opinion_mcp" / "services" / "job_manager.py"
WORKFLOW_STATUS_PATH = ROOT / "app" / "services" / "workflow_status.py"
USER_SETTINGS_PATH = ROOT / "app" / "services" / "user_settings.py"


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


def _load_job_manager_module():
    _stub_logger()

    schemas_stub = types.ModuleType("opinion_mcp.schemas")

    class JobStatus:
        PENDING = "pending"
        RUNNING = "running"
        COMPLETED = "completed"
        FAILED = "failed"

    class AnalysisResult:
        def __init__(self):
            self.copywriting = None
            self.cards = None
            self.ai_images = []
            self.sources_analyzed = []
            self.skipped_sources = []
            self.evidence_count = 0
            self.source_stats = {}
            self.output_file = None
            self.summary = ""
            self.insight = ""
            self.title = ""
            self.subtitle = ""

    class AnalysisCards:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class Copywriting:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class CopywritingUpdate:
        pass

    class JobInfo:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.result = kwargs.get("result")
            self.started_at = kwargs.get("started_at")
            self.completed_at = kwargs.get("completed_at")
            self.status = kwargs.get("status")
            self.progress = kwargs.get("progress", 0)
            self.current_step = kwargs.get("current_step")
            self.current_step_name = kwargs.get("current_step_name")
            self.current_source = kwargs.get("current_source")
            self.error_message = kwargs.get("error_message")
            self.webhook_url = kwargs.get("webhook_url")

        @property
        def is_running(self):
            return self.status == JobStatus.RUNNING

        @property
        def is_completed(self):
            return self.status == JobStatus.COMPLETED

        @property
        def is_failed(self):
            return self.status == JobStatus.FAILED

    schemas_stub.JobInfo = JobInfo
    schemas_stub.JobStatus = JobStatus
    schemas_stub.AnalysisResult = AnalysisResult
    schemas_stub.AnalysisCards = AnalysisCards
    schemas_stub.Copywriting = Copywriting
    schemas_stub.CopywritingUpdate = CopywritingUpdate
    sys.modules["opinion_mcp.schemas"] = schemas_stub

    spec = importlib.util.spec_from_file_location(
        "test_job_manager_module", JOB_MANAGER_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_workflow_status_module():
    spec = importlib.util.spec_from_file_location(
        "test_workflow_status_module", WORKFLOW_STATUS_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_user_settings_module():
    spec = importlib.util.spec_from_file_location(
        "test_user_settings_module", USER_SETTINGS_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_job_manager_isolates_current_job_per_account():
    module = _load_job_manager_module()
    manager = module.JobManager()

    job_a = manager.create_job(topic="Topic A", account_id="acct-a")
    manager.update_status(job_a, status=module.JobStatus.RUNNING)
    job_b = manager.create_job(topic="Topic B", account_id="acct-b")

    assert manager.get_current_job(account_id="acct-a").job_id == job_a
    assert manager.get_current_job(account_id="acct-b").job_id == job_b
    assert manager.get_job(job_a, account_id="acct-a").topic == "Topic A"
    assert manager.get_job(job_b, account_id="acct-b").topic == "Topic B"
    assert manager.get_job(job_a, account_id="acct-b") is None


@pytest.mark.asyncio
async def test_workflow_status_tracks_state_per_account():
    module = _load_workflow_status_module()
    manager = module.WorkflowStatusManager()

    await manager.start_workflow("Topic A", account_id="acct-a")
    await manager.start_workflow("Topic B", account_id="acct-b")
    await manager.update_step("reporter", account_id="acct-a")

    status_a = await manager.get_status(account_id="acct-a")
    status_b = await manager.get_status(account_id="acct-b")

    assert status_a["topic"] == "Topic A"
    assert status_a["current_step"] == "reporter"
    assert status_b["topic"] == "Topic B"
    assert status_b["current_step"] == "source_retriever"


def test_user_settings_persists_separate_files_per_account(tmp_path):
    module = _load_user_settings_module()
    module._SETTINGS_DIR = tmp_path

    module.update_user_settings(account_id="acct-a", llm_apis=[{"key": "A"}])
    module.update_user_settings(account_id="acct-b", llm_apis=[{"key": "B"}])

    settings_a = module.load_user_settings(account_id="acct-a")
    settings_b = module.load_user_settings(account_id="acct-b")

    assert settings_a["llm_apis"] == [{"key": "A"}]
    assert settings_b["llm_apis"] == [{"key": "B"}]
    assert (tmp_path / "acct-a.json").exists()
    assert (tmp_path / "acct-b.json").exists()
