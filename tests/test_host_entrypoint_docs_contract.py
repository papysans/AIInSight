from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ai_topic_analyzer_skill_documents_discovery_phase():
    content = (
        ROOT / ".agents" / "skills" / "ai-topic-analyzer" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert "Phase 1: Discovery" in content
    assert "Phase 2: Evidence" in content
    assert "analysis_packet" in content
    assert "render_cards" in content


def test_ai_insight_skill_documents_pulse_phase():
    content = (ROOT / ".agents" / "skills" / "ai-insight" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "Phase 1: Pulse" in content
    assert "daily_topics" in content
    assert "render_cards" in content


def test_mcp_server_exposes_six_capability_tools():
    content = (ROOT / "opinion_mcp" / "server.py").read_text(encoding="utf-8")
    assert 'name="render_cards"' in content
    assert 'name="publish_xhs_note"' in content
    assert 'name="check_xhs_status"' in content
    assert 'name="get_xhs_login_qrcode"' in content
    assert 'name="check_xhs_login_session"' in content
    assert 'name="submit_xhs_verification"' in content
    assert '"render_cards": render_cards' in content
    assert '"publish_xhs_note": publish_xhs_note' in content


def test_host_runtime_doc_describes_capability_backend():
    content = (ROOT / "docs" / "HOST_CONTROLLED_RUNTIME.md").read_text(encoding="utf-8")
    assert "renderer" in content
    assert "XHS" in content
    assert "publish" in content
