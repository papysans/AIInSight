from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
SERVICE_PATH = ROOT / "app" / "services" / "publish" / "ai_daily_publish_service.py"


def _load_publish_service_module():
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

    xhs_stub_module = types.ModuleType("app.services.xiaohongshu_publisher")
    setattr(
        xhs_stub_module,
        "xiaohongshu_publisher",
        types.SimpleNamespace(publish_content=None),
    )
    sys.modules["app.services.xiaohongshu_publisher"] = xhs_stub_module

    renderer_stub_module = types.ModuleType("app.services.card_render_client")
    setattr(renderer_stub_module, "card_render_client", types.SimpleNamespace())
    sys.modules["app.services.card_render_client"] = renderer_stub_module

    pipeline_stub_module = types.ModuleType("app.services.ai_daily_pipeline")

    async def _unused_get_topic_by_id(topic_id: str):
        return None

    async def _unused_collect_ai_daily(force_refresh: bool = False):
        return None

    setattr(pipeline_stub_module, "get_topic_by_id", _unused_get_topic_by_id)
    setattr(pipeline_stub_module, "collect_ai_daily", _unused_collect_ai_daily)
    sys.modules["app.services.ai_daily_pipeline"] = pipeline_stub_module

    spec = importlib.util.spec_from_file_location(
        "test_ai_daily_publish_service_module", SERVICE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _topic(
    title: str,
    summary_zh: str = "",
    *,
    tags: list[str] | None = None,
    source_count: int = 1,
    source_type: str = "media",
    source: str = "aibase",
    final_score: float = 90.0,
):
    return SimpleNamespace(
        title=title,
        summary_zh=summary_zh,
        tags=tags or [],
        source_count=source_count,
        final_score=final_score,
        sources=[SimpleNamespace(source=source, source_type=source_type)],
    )


def test_compose_editorial_ranking_copy_produces_day_level_takeaway_and_supporting_points():
    module = _load_publish_service_module()
    topics = [
        _topic(
            "OpenAI 发布新一代图像能力",
            "图像生成直接进入主产品工作流，开发者接入成本继续下降。",
            tags=["OpenAI", "多模态"],
            source_count=4,
            source_type="product",
            source="techcrunch_ai",
        ),
        _topic(
            "bytedance/deer-flow 冲上 GitHub Trending",
            "自动化工作流和 AI Agent 工具继续升温，开发者讨论度很高。",
            tags=["开源", "Agent"],
            source_count=3,
            source_type="code",
            source="github_trending",
        ),
        _topic(
            "MiniAppBench 刷新评测基准",
            "研究和应用评测都在往真实使用场景靠。",
            tags=["论文", "评测"],
            source_count=2,
            source_type="research",
            source="hf_papers",
        ),
    ]

    content = module._compose_editorial_ranking_copy("2026-03-11", topics)

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    assert len(lines) >= 4
    assert "今天" in lines[0]
    assert "AI" in lines[0]
    assert not any(line.startswith("1.") for line in lines)
    assert any("OpenAI" in line for line in lines[1:])
    assert any("GitHub" in line or "开源" in line for line in lines[1:])
    assert any(
        "值得看" in line or "更像" in line or "Bottom line" in line for line in lines
    )


def test_compose_editorial_ranking_copy_falls_back_to_neutral_factual_wording_for_low_signal_topics():
    module = _load_publish_service_module()
    topics = [
        _topic(
            "msitarzewski/agency-agents",
            "msitarzewski/agency-agents",
            tags=[],
            source_count=1,
            source_type="code",
            source="github_trending",
        ),
        _topic(
            "Another AI repo update",
            "A very long but low-signal English-only scraped snippet that mostly repeats the repository title without adding clear context.",
            tags=[],
            source_count=1,
            source_type="code",
            source="github_trending",
        ),
    ]

    content = module._compose_editorial_ranking_copy("2026-03-11", topics)

    assert "A very long but low-signal English-only scraped snippet" not in content
    assert "msitarzewski/agency-agents" in content or "agency-agents" in content
    assert "今天" in content
    assert "爆了" not in content
    assert "颠覆" not in content
    assert "发酵" not in content


def test_compose_editorial_ranking_copy_handles_empty_or_repeated_summaries_without_dumping_fragments():
    module = _load_publish_service_module()
    topics = [
        _topic(
            "OpenAI 发布新能力",
            "OpenAI 发布新能力",
            tags=["OpenAI"],
            source_count=2,
            source_type="product",
            source="techcrunch_ai",
        ),
        _topic(
            "开源 Agent 工具热度上来",
            "",
            tags=["开源", "Agent"],
            source_count=1,
            source_type="code",
            source="github_trending",
        ),
    ]

    content = module._compose_editorial_ranking_copy("2026-03-11", topics)

    assert content.count("OpenAI 发布新能力") == 1
    assert "今天 AI 圈" in content
    assert "Bottom line" in content
    assert "1." not in content


@pytest.mark.asyncio
async def test_publish_ai_daily_ranking_preserves_explicit_content_override(
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_publish_service_module()
    ranking = SimpleNamespace(
        date="2026-03-11",
        total=2,
        topics=[
            _topic("OpenAI 发布新能力", "今天的重点是产品化速度继续加快。"),
            _topic("开源 Agent 工具热度上来", "工作流和部署正在变成更实际的话题。"),
        ],
    )
    captured: dict[str, object] = {}

    async def fake_collect_ai_daily(force_refresh: bool = False):
        return ranking

    async def fake_generate_cards(
        limit: int, title: str | None = None, card_types: list[str] | None = None
    ):
        return {
            "success": True,
            "cards": {
                "title": {
                    "success": True,
                    "image_data_url": "data:image/png;base64,title",
                },
                "daily-rank": {
                    "success": True,
                    "image_data_url": "data:image/png;base64,rank",
                },
            },
        }

    async def fake_default_tags(topics, custom_tags=None):
        return ["AI热点"]

    async def fake_publish_content(title, content, images, tags=None):
        captured.update(
            {"title": title, "content": content, "images": images, "tags": tags}
        )
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(module, "collect_ai_daily", fake_collect_ai_daily)
    monkeypatch.setattr(module, "generate_ai_daily_ranking_cards", fake_generate_cards)
    monkeypatch.setattr(module, "_default_ranking_tags", fake_default_tags)
    monkeypatch.setattr(
        module.xiaohongshu_publisher, "publish_content", fake_publish_content
    )

    result = await module.publish_ai_daily_ranking(
        content="这段是我手动写的正文，不要被默认生成逻辑改写。"
    )

    assert result["success"] is True
    assert captured["content"] == "这段是我手动写的正文，不要被默认生成逻辑改写。"


@pytest.mark.asyncio
async def test_publish_ai_daily_ranking_uses_generated_editorial_copy_by_default(
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_publish_service_module()
    ranking = SimpleNamespace(
        date="2026-03-11",
        total=3,
        topics=[
            _topic(
                "OpenAI 发布新一代图像能力",
                "图像生成直接进入主产品工作流，开发者接入成本继续下降。",
                tags=["OpenAI", "多模态"],
                source_count=4,
                source_type="product",
                source="techcrunch_ai",
            ),
            _topic(
                "bytedance/deer-flow 冲上 GitHub Trending",
                "自动化工作流和 AI Agent 工具继续升温，开发者讨论度很高。",
                tags=["开源", "Agent"],
                source_count=3,
                source_type="code",
                source="github_trending",
            ),
            _topic(
                "MiniAppBench 刷新评测基准",
                "研究和应用评测都在往真实使用场景靠。",
                tags=["论文", "评测"],
                source_count=2,
                source_type="research",
                source="hf_papers",
            ),
        ],
    )
    captured: dict[str, object] = {}

    async def fake_collect_ai_daily(force_refresh: bool = False):
        return ranking

    async def fake_generate_cards(
        limit: int, title: str | None = None, card_types: list[str] | None = None
    ):
        return {
            "success": True,
            "cards": {
                "title": {
                    "success": True,
                    "image_data_url": "data:image/png;base64,title",
                },
                "daily-rank": {
                    "success": True,
                    "image_data_url": "data:image/png;base64,rank",
                },
            },
        }

    async def fake_default_tags(topics, custom_tags=None):
        return ["AI热点", "人工智能"]

    async def fake_publish_content(title, content, images, tags=None):
        captured.update(
            {"title": title, "content": content, "images": images, "tags": tags}
        )
        return {"success": True, "message": "ok"}

    monkeypatch.setattr(module, "collect_ai_daily", fake_collect_ai_daily)
    monkeypatch.setattr(module, "generate_ai_daily_ranking_cards", fake_generate_cards)
    monkeypatch.setattr(module, "_default_ranking_tags", fake_default_tags)
    monkeypatch.setattr(
        module.xiaohongshu_publisher, "publish_content", fake_publish_content
    )

    result = await module.publish_ai_daily_ranking()

    assert result["success"] is True
    assert isinstance(captured["content"], str)
    assert "今天 AI 圈" in str(captured["content"])
    assert "Bottom line" in str(captured["content"])
    assert "1." not in str(captured["content"])
