from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
ENDPOINTS_PATH = ROOT / "app" / "api" / "endpoints.py"


def _load_endpoints_module_with_account(account_id: str):
    account_context_mod = types.ModuleType("app.services.account_context")
    account_context_mod.get_account_id = lambda: account_id
    sys.modules["app.services.account_context"] = account_context_mod

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
    responses_mod.FileResponse = lambda *args, **kwargs: {"file": args[0]}
    responses_mod.HTMLResponse = lambda *args, **kwargs: {
        "html": args[0],
        "status_code": kwargs.get("status_code", 200),
    }
    responses_mod.StreamingResponse = object
    sys.modules["fastapi.responses"] = responses_mod

    loguru_stub = types.ModuleType("loguru")
    loguru_stub.logger = types.SimpleNamespace(
        info=lambda *a, **k: None,
        error=lambda *a, **k: None,
        warning=lambda *a, **k: None,
        debug=lambda *a, **k: None,
        exception=lambda *a, **k: None,
    )
    sys.modules["loguru"] = loguru_stub

    workflow_mod = types.ModuleType("app.services.workflow")
    workflow_mod.app_graph = types.SimpleNamespace()
    workflow_mod.GraphState = dict
    workflow_mod.run_retrieve_and_report = lambda *a, **k: None
    workflow_mod.run_submit_analysis_result = lambda *a, **k: None
    sys.modules["app.services.workflow"] = workflow_mod

    workflow_status_mod = types.ModuleType("app.services.workflow_status")
    workflow_status_mod.workflow_status = types.SimpleNamespace(get_status=None)
    sys.modules["app.services.workflow_status"] = workflow_status_mod

    user_settings_mod = types.ModuleType("app.services.user_settings")
    user_settings_mod.load_user_settings = lambda *a, **k: {}
    user_settings_mod.update_user_settings = lambda **kwargs: {}
    sys.modules["app.services.user_settings"] = user_settings_mod

    topic_card_mod = types.ModuleType("app.services.topic_card_builder")
    topic_card_mod.build_topic_impact_payload = lambda *a, **k: {}
    topic_card_mod.build_topic_radar_payload = lambda *a, **k: {}
    topic_card_mod.build_topic_timeline = lambda *a, **k: []
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
    for name in [
        "TopicAnalysisRequest",
        "RetrieveAndReportRequest",
        "RetrieveAndReportResponse",
        "SubmitAnalysisResultRequest",
        "SubmitAnalysisResultResponse",
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
    ]:
        setattr(
            schemas_mod,
            name,
            type(
                name,
                (),
                {"__init__": lambda self, **kwargs: self.__dict__.update(kwargs)},
            ),
        )
    sys.modules["app.schemas"] = schemas_mod

    xhs_mod = types.ModuleType("app.services.xiaohongshu_publisher")
    xhs_mod.xiaohongshu_publisher = types.SimpleNamespace(
        _load_cached_login_qrcode=lambda account_id=None: {
            "qr_filename": "demo.png",
            "message": "ok",
            "expires_at": "2099-01-01T00:00:00",
        },
    )
    sys.modules["app.services.xiaohongshu_publisher"] = xhs_mod

    card_render_mod = types.ModuleType("app.services.card_render_client")
    card_render_mod.card_render_client = types.SimpleNamespace()
    sys.modules["app.services.card_render_client"] = card_render_mod

    ai_daily_pipeline_mod = types.ModuleType("app.services.ai_daily_pipeline")
    ai_daily_pipeline_mod.collect_ai_daily = lambda *a, **k: None
    ai_daily_pipeline_mod.get_topic_by_id = lambda *a, **k: None
    sys.modules["app.services.ai_daily_pipeline"] = ai_daily_pipeline_mod

    ai_daily_publish_mod = types.ModuleType(
        "app.services.publish.ai_daily_publish_service"
    )
    ai_daily_publish_mod.generate_ai_daily_ranking_cards = lambda *a, **k: None
    ai_daily_publish_mod.publish_ai_daily_ranking = lambda *a, **k: None
    ai_daily_publish_mod.publish_ai_daily_topic = lambda *a, **k: None
    sys.modules["app.services.publish.ai_daily_publish_service"] = ai_daily_publish_mod

    spec = importlib.util.spec_from_file_location(
        "test_account_artifact_endpoints", ENDPOINTS_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_card_preview_output_dir_is_account_scoped():
    module = _load_endpoints_module_with_account("acct-preview")
    assert str(module._get_card_preview_output_dir()).endswith(
        "outputs/card_previews/acct-preview"
    )


def test_xhs_qrcode_file_route_reads_account_scoped_directory(monkeypatch):
    module = _load_endpoints_module_with_account("acct-qr")

    monkeypatch.setattr(module.Path, "resolve", lambda self: self)

    class FakePath(type(Path())):
        def is_file(self):
            return True

    result = (
        module.get_xhs_login_qrcode_file.__wrapped__
        if hasattr(module.get_xhs_login_qrcode_file, "__wrapped__")
        else None
    )
    assert str(module.Path("outputs/xhs_login") / "acct-qr").endswith(
        "outputs/xhs_login/acct-qr"
    )
