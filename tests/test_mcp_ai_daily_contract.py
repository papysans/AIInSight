from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "opinion_mcp" / "server.py"
AI_DAILY_PATH = ROOT / "opinion_mcp" / "tools" / "ai_daily.py"


def _load_ai_daily_module():
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
            BACKEND_URL="http://localhost:8000",
            REQUEST_TIMEOUT=300,
        ),
    )
    sys.modules["opinion_mcp.config"] = config_stub

    spec = importlib.util.spec_from_file_location("test_ai_daily_module", AI_DAILY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upload_xhs_cookies_public_schema_uses_string_contract():
    server_source = SERVER_PATH.read_text(encoding="utf-8")

    assert 'name="upload_xhs_cookies"' in server_source
    assert '"cookies_data": {' in server_source
    assert '"type": "string"' in server_source
    assert '"type": ["array", "object", "string"]' not in server_source


@pytest.mark.asyncio
async def test_analyze_ai_topic_calls_dedicated_ai_daily_endpoint(
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_ai_daily_module()
    calls: list[tuple[str, dict[str, str], int]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "topic_id": "topic_123",
                "depth": "deep",
                "analysis": {"final_copy": "AI 热点分析结果"},
            }

    class FakeAsyncClient:
        def __init__(self, timeout: int):
            self.timeout = timeout

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

        async def post(self, url: str, json: dict[str, str]) -> FakeResponse:
            calls.append((url, json, self.timeout))
            return FakeResponse()

    monkeypatch.setattr(module.httpx, "AsyncClient", FakeAsyncClient)

    result = await module.analyze_ai_topic("topic_123", depth="deep")

    assert calls == [
        (
            "http://localhost:8000/api/ai-daily/topic_123/analyze",
            {"depth": "deep"},
            300,
        )
    ]
    assert result == {
        "success": True,
        "topic_id": "topic_123",
        "depth": "deep",
        "analysis": {"final_copy": "AI 热点分析结果"},
    }
