from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS_PATH = ROOT / "app" / "api" / "endpoints.py"


def _load_endpoints_module():
    fastapi_mod = types.ModuleType("fastapi")

    class APIRouter:
        def get(self, *args, **kwargs):
            return lambda fn: fn

        def post(self, *args, **kwargs):
            return lambda fn: fn

        def put(self, *args, **kwargs):
            return lambda fn: fn

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            self.status_code = status_code
            self.detail = detail

    class Request:
        url_for = lambda self, *args, **kwargs: types.SimpleNamespace(path="/mock")

    fastapi_mod.APIRouter = APIRouter
    fastapi_mod.HTTPException = HTTPException
    fastapi_mod.Request = Request
    sys.modules["fastapi"] = fastapi_mod

    responses_mod = types.ModuleType("fastapi.responses")
    responses_mod.FileResponse = object
    responses_mod.HTMLResponse = object
    responses_mod.StreamingResponse = object
    sys.modules["fastapi.responses"] = responses_mod

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

    workflow_mod = types.ModuleType("app.services.workflow")
    workflow_mod.app_graph = types.SimpleNamespace()
    workflow_mod.GraphState = dict
    workflow_mod.run_retrieve_and_report = None
    workflow_mod.run_submit_analysis_result = None
    sys.modules["app.services.workflow"] = workflow_mod

    workflow_status_mod = types.ModuleType("app.services.workflow_status")
    workflow_status_mod.workflow_status = types.SimpleNamespace(get_status=None)
    sys.modules["app.services.workflow_status"] = workflow_status_mod

    user_settings_mod = types.ModuleType("app.services.user_settings")
    user_settings_mod.load_user_settings = lambda: {}
    user_settings_mod.update_user_settings = lambda **kwargs: {}
    sys.modules["app.services.user_settings"] = user_settings_mod

    topic_card_mod = types.ModuleType("app.services.topic_card_builder")
    topic_card_mod.build_topic_impact_payload = lambda *args, **kwargs: {}
    topic_card_mod.build_topic_radar_payload = lambda *args, **kwargs: {}
    topic_card_mod.build_topic_timeline = lambda *args, **kwargs: []
    sys.modules["app.services.topic_card_builder"] = topic_card_mod

    config_mod = types.ModuleType("app.config")
    config_mod.settings = types.SimpleNamespace(
        AGENT_CONFIG={"reporter": [], "analyst": [], "debater": [], "writer": []},
        DEBATE_MAX_ROUNDS=5,
        DEFAULT_SOURCE_GROUPS=["media"],
        AI_DAILY_CONFIG={"preview_output_dir": "outputs/card_previews"},
        get_available_sources=lambda: ["hn"],
        get_all_models=lambda: {},
        validate_model=lambda provider, model: True,
        get_models_for_provider=lambda provider: [],
    )
    sys.modules["app.config"] = config_mod

    schemas_mod = types.ModuleType("app.schemas")

    class _Schema:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    for name in [
        "TopicAnalysisRequest",
        "AgentState",
        "ConfigResponse",
        "ConfigUpdateRequest",
        "UserSettingsResponse",
        "UserSettingsUpdateRequest",
        "OutputFileListResponse",
        "OutputFileInfo",
        "OutputFileContentResponse",
        "WorkflowStatusResponse",
        "LLMProviderConfig",
        "XhsPublishRequest",
        "XhsLoginQrcodeResponse",
        "XhsUploadCookiesRequest",
        "XhsUploadCookiesResponse",
        "TitleCardRenderRequest",
        "RadarCardRenderRequest",
        "TimelineCardRenderRequest",
        "TrendCardRenderRequest",
        "ImpactCardRenderRequest",
        "DailyRankCardRenderRequest",
        "HotTopicCardRenderRequest",
        "CardRenderResponse",
        "AiDailyCollectRequest",
        "AiDailyResponse",
        "AiDailyTopicDetailResponse",
        "AiDailyAnalyzeRequest",
        "AiDailyCardsRequest",
        "AiDailyPublishRequest",
        "AiDailyRankingCardsRequest",
        "AiDailyRankingPublishRequest",
        "TopicCardsRequest",
        "RetrieveAndReportRequest",
        "RetrieveAndReportResponse",
        "SubmitAnalysisResultRequest",
        "SubmitAnalysisResultResponse",
    ]:
        setattr(schemas_mod, name, type(name, (_Schema,), {}))
    sys.modules["app.schemas"] = schemas_mod

    card_render_mod = types.ModuleType("app.services.card_render_client")
    card_render_mod.card_render_client = types.SimpleNamespace()
    sys.modules["app.services.card_render_client"] = card_render_mod

    ai_daily_pipeline_mod = types.ModuleType("app.services.ai_daily_pipeline")
    ai_daily_pipeline_mod.collect_ai_daily = lambda *args, **kwargs: None
    ai_daily_pipeline_mod.get_topic_by_id = lambda *args, **kwargs: None
    sys.modules["app.services.ai_daily_pipeline"] = ai_daily_pipeline_mod

    ai_daily_publish_mod = types.ModuleType(
        "app.services.publish.ai_daily_publish_service"
    )
    ai_daily_publish_mod.generate_ai_daily_ranking_cards = lambda *args, **kwargs: None
    ai_daily_publish_mod.publish_ai_daily_ranking = lambda *args, **kwargs: None
    ai_daily_publish_mod.publish_ai_daily = lambda *args, **kwargs: None
    sys.modules["app.services.publish.ai_daily_publish_service"] = ai_daily_publish_mod

    spec = importlib.util.spec_from_file_location(
        "test_workflow_split_endpoints_module", ENDPOINTS_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_retrieve_and_report_endpoint_calls_split_workflow(monkeypatch):
    module = _load_endpoints_module()

    class RequestPayload:
        topic = "AI Infra"
        source_groups = ["media"]
        source_names = None
        depth = "standard"
        evidence_mode = "summary"

    async def fake_run_retrieve_and_report(state):
        assert state == {
            "topic": "AI Infra",
            "source_groups": ["media"],
            "source_names": None,
            "depth": "standard",
            "evidence_mode": "summary",
            "account_id": "_default",
        }
        return {
            "topic": "AI Infra",
            "evidence_bundle": {"items": [{"id": "e1"}]},
            "source_stats": {"hn": 2},
            "news_content": "cloud-side summary",
            "messages": ["Reporter: cloud-side summary"],
            "safety_blocked": False,
            "safety_reason": None,
        }

    monkeypatch.setattr(module, "run_retrieve_and_report", fake_run_retrieve_and_report)

    result = await module.retrieve_and_report(RequestPayload())

    assert result.topic == "AI Infra"
    assert result.evidence_bundle == {"items": [{"id": "e1"}]}
    assert result.news_content == "cloud-side summary"


@pytest.mark.asyncio
async def test_retrieve_and_report_rejects_unknown_evidence_mode():
    module = _load_endpoints_module()

    class RequestPayload:
        topic = "AI Infra"
        source_groups = ["media"]
        source_names = None
        depth = "standard"
        evidence_mode = "huge"

    with pytest.raises(module.HTTPException):
        await module.retrieve_and_report(RequestPayload())


@pytest.mark.asyncio
async def test_submit_analysis_result_endpoint_calls_split_back_half(monkeypatch):
    module = _load_endpoints_module()

    class RequestPayload:
        topic = "AI Infra"
        news_content = "cloud-side summary"
        final_analysis = "host debate final analysis"
        debate_history = ["Analyst round 1", "Debater round 1"]
        source_stats = {"hn": 2}
        image_count = 1
        xhs_publish_enabled = False

    async def fake_run_submit_analysis_result(state):
        assert state["topic"] == "AI Infra"
        assert state["final_analysis"] == "host debate final analysis"
        assert state["debate_history"] == ["Analyst round 1", "Debater round 1"]
        return {
            "topic": "AI Infra",
            "final_copy": "TITLE: demo\nCONTENT:\nbody",
            "output_file": "outputs/demo.md",
            "image_urls": ["https://img.example/1.png"],
            "xhs_publish_result": {"success": True},
            "messages": ["Writer: demo"],
        }

    monkeypatch.setattr(
        module, "run_submit_analysis_result", fake_run_submit_analysis_result
    )

    result = await module.submit_analysis_result(RequestPayload())

    assert result.final_copy == "TITLE: demo\nCONTENT:\nbody"
    assert result.image_urls == ["https://img.example/1.png"]
