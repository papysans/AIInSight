from __future__ import annotations

import importlib.util
import io
from pathlib import Path
import sys
import types
from types import SimpleNamespace
from unittest.mock import mock_open, patch

import pytest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / "app" / "services" / "workflow.py"


def _load_workflow_module():
    graph_mod = types.ModuleType("langgraph.graph")

    class FakeStateGraph:
        def __init__(self, *args, **kwargs):
            pass

        def add_node(self, *args, **kwargs):
            return None

        def set_entry_point(self, *args, **kwargs):
            return None

        def add_edge(self, *args, **kwargs):
            return None

        def add_conditional_edges(self, *args, **kwargs):
            return None

        def compile(self):
            class _Graph:
                async def astream(self, initial_state):
                    if False:
                        yield initial_state

            return _Graph()

    graph_mod.StateGraph = FakeStateGraph
    graph_mod.END = "END"
    sys.modules["langgraph.graph"] = graph_mod

    messages_mod = types.ModuleType("langchain_core.messages")

    class FakeMessage:
        def __init__(self, content: str):
            self.content = content

    messages_mod.SystemMessage = FakeMessage
    messages_mod.HumanMessage = FakeMessage
    sys.modules["langchain_core.messages"] = messages_mod

    llm_mod = types.ModuleType("app.llm")
    llm_mod.get_agent_llm = lambda agent: None
    sys.modules["app.llm"] = llm_mod

    config_mod = types.ModuleType("app.config")
    config_mod.settings = SimpleNamespace(
        DEFAULT_SOURCE_GROUPS=["media"],
        DEPTH_PRESETS={"standard": {"debate_rounds": 2}},
        DEBATE_MAX_ROUNDS=5,
        WORKFLOW_CONTENT_SAFETY={},
        XHS_MCP_CONFIG={"auto_publish": False},
    )
    sys.modules["app.config"] = config_mod

    retriever_mod = types.ModuleType("app.services.topic_evidence_retriever")
    retriever_mod.topic_evidence_retriever = SimpleNamespace(retrieve=None)
    sys.modules["app.services.topic_evidence_retriever"] = retriever_mod

    schemas_mod = types.ModuleType("app.schemas")
    schemas_mod.EvidenceBundle = object
    sys.modules["app.schemas"] = schemas_mod

    image_mod = types.ModuleType("app.services.image_generator")
    image_mod.image_generator_service = SimpleNamespace(generate_images=None)
    sys.modules["app.services.image_generator"] = image_mod

    xhs_mod = types.ModuleType("app.services.xiaohongshu_publisher")
    xhs_mod.xiaohongshu_publisher = SimpleNamespace(
        get_status=None, publish_content=None
    )
    sys.modules["app.services.xiaohongshu_publisher"] = xhs_mod

    workflow_status_mod = types.ModuleType("app.services.workflow_status")
    workflow_status_mod.workflow_status = SimpleNamespace(update_step=None)
    sys.modules["app.services.workflow_status"] = workflow_status_mod

    spec = importlib.util.spec_from_file_location(
        "test_workflow_split_module", WORKFLOW_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.asyncio
async def test_run_retrieve_and_report_returns_front_half_contract(
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_workflow_module()
    calls: list[str] = []

    async def fake_source_retriever_node(state):
        calls.append("source_retriever")
        assert state["topic"] == "AI Infra"
        return {
            "evidence_bundle": {"items": [{"id": "e1"}]},
            "source_stats": {"hn": 2},
            "messages": ["retrieved"],
        }

    async def fake_reporter_node(state):
        calls.append("reporter")
        assert state["evidence_bundle"] == {"items": [{"id": "e1"}]}
        assert state["source_stats"] == {"hn": 2}
        return {
            "news_content": "cloud-side summary",
            "messages": ["Reporter: cloud-side summary"],
        }

    monkeypatch.setattr(module, "source_retriever_node", fake_source_retriever_node)
    monkeypatch.setattr(module, "reporter_node", fake_reporter_node)

    result = await module.run_retrieve_and_report(
        {
            "topic": "AI Infra",
            "source_groups": ["media"],
            "source_names": None,
            "depth": "standard",
        }
    )

    assert calls == ["source_retriever", "reporter"]
    assert result["evidence_bundle"] == {"items": [{"id": "e1"}]}
    assert result["source_stats"] == {"hn": 2}
    assert result["news_content"] == "cloud-side summary"


@pytest.mark.asyncio
async def test_run_submit_analysis_result_threads_final_analysis_through_back_half(
    monkeypatch: pytest.MonkeyPatch,
):
    module = _load_workflow_module()
    captured: dict[str, dict] = {}

    async def fake_writer_node(state):
        captured["writer"] = dict(state)
        return {
            "final_copy": "TITLE: demo\nCONTENT:\nbody",
            "output_file": "outputs/demo.md",
            "messages": ["Writer: demo"],
        }

    async def fake_image_generator_node(state):
        captured["image"] = dict(state)
        return {
            "image_urls": ["https://img.example/1.png"],
            "messages": ["Image Generator: Generated 1 images."],
        }

    async def fake_xhs_publisher_node(state):
        captured["xhs"] = dict(state)
        return {
            "xhs_publish_result": {"success": True},
            "messages": ["XHS Publisher: ok"],
        }

    monkeypatch.setattr(module, "writer_node", fake_writer_node)
    monkeypatch.setattr(module, "image_generator_node", fake_image_generator_node)
    monkeypatch.setattr(module, "xiaohongshu_publisher_node", fake_xhs_publisher_node)

    result = await module.run_submit_analysis_result(
        {
            "topic": "AI Infra",
            "news_content": "source-backed summary",
            "final_analysis": "host debate final analysis",
            "debate_history": ["Analyst round 1", "Debater round 1"],
            "source_stats": {"hn": 2},
            "image_count": 1,
        }
    )

    assert captured["writer"]["initial_analysis"] == "host debate final analysis"
    assert captured["writer"]["debate_history"] == [
        "Analyst round 1",
        "Debater round 1",
    ]
    assert captured["image"]["final_copy"] == "TITLE: demo\nCONTENT:\nbody"
    assert captured["xhs"]["image_urls"] == ["https://img.example/1.png"]
    assert result["final_copy"] == "TITLE: demo\nCONTENT:\nbody"
    assert result["image_urls"] == ["https://img.example/1.png"]
    assert result["xhs_publish_result"] == {"success": True}


@pytest.mark.asyncio
async def test_writer_node_includes_analysis_in_prompt(monkeypatch: pytest.MonkeyPatch):
    module = _load_workflow_module()
    captured: dict[str, str] = {}

    class FakeLLM:
        async def ainvoke(self, messages):
            captured["human"] = messages[1].content
            return SimpleNamespace(content="TITLE: demo\nCONTENT:\nbody")

    monkeypatch.setattr(module, "get_agent_llm", lambda agent: FakeLLM())
    monkeypatch.setattr(module.os, "makedirs", lambda *args, **kwargs: None)

    with patch("builtins.open", mock_open()):
        await module.writer_node(
            {
                "topic": "AI Infra",
                "news_content": "source-backed summary",
                "initial_analysis": "host debate final analysis",
                "source_stats": {"hn": 2},
                "debate_history": ["r1"],
            }
        )

    assert "host debate final analysis" in captured["human"]
