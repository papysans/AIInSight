"""
Skill-driven architecture contract tests.
Validates that Skill output schemas and MCP tool definitions conform to
the canonical contracts in .agents/skills/shared/GUIDELINES.md
"""
import hashlib
import json
from datetime import date
from pathlib import Path

import pytest


class TestAnalysisPacketSchema:
    """Validate analysis_packet structure per GUIDELINES.md Section 2.1"""

    REQUIRED_FIELDS = [
        "topic_id", "title", "summary", "insight",
        "signals", "actions", "confidence", "tags",
        "xhs_copy", "debate_log", "sources"
    ]

    def test_required_fields_present(self):
        """analysis_packet must contain all required fields"""
        packet = self._make_minimal_packet()
        for field in self.REQUIRED_FIELDS:
            assert field in packet, f"Missing required field: {field}"

    def test_topic_id_format(self):
        """topic_id = YYYYMMDD_ + SHA1(canonical_title)[0:8]"""
        title = "Test Topic"
        expected_hash = hashlib.sha1(title.encode()).hexdigest()[:8]
        today = date.today().strftime("%Y%m%d")
        expected_id = f"{today}_{expected_hash}"

        packet = self._make_minimal_packet(title=title)
        assert packet["topic_id"] == expected_id

    def test_signals_structure(self):
        """Each signal must have label and value"""
        packet = self._make_minimal_packet()
        for signal in packet["signals"]:
            assert "label" in signal
            assert "value" in signal
            assert signal["value"] in ("Strong", "Moderate", "Weak")

    def test_confidence_range(self):
        """confidence must be 0-1"""
        packet = self._make_minimal_packet()
        assert 0 <= packet["confidence"] <= 1

    def test_xhs_copy_structure(self):
        """xhs_copy must have title, content, tags"""
        packet = self._make_minimal_packet()
        xhs = packet["xhs_copy"]
        assert "title" in xhs
        assert "content" in xhs
        assert "tags" in xhs
        assert isinstance(xhs["tags"], list)

    @staticmethod
    def _make_minimal_packet(title="Test Topic"):
        today = date.today().strftime("%Y%m%d")
        hash_part = hashlib.sha1(title.encode()).hexdigest()[:8]
        return {
            "topic_id": f"{today}_{hash_part}",
            "title": title,
            "subtitle": "副标题",
            "summary": "这是一个20-25字的核心观点摘要测试",
            "insight": "这是100字以内的深度洞察" * 3,
            "signals": [
                {"label": "技术成熟度", "value": "Strong", "desc": "已有多个生产部署"},
                {"label": "市场需求", "value": "Moderate", "desc": "需求增长中"},
            ],
            "actions": ["关注后续发展", "评估技术适用性"],
            "confidence": 0.85,
            "tags": ["#AI", "#测试"],
            "xhs_copy": {
                "title": "🔥 测试标题",
                "content": "小红书正文内容...",
                "tags": ["AI", "测试"],
            },
            "debate_log": ["Round 1: Analyst: 分析...", "Round 1: Debater: PASS"],
            "sources": ["https://example.com"],
        }


class TestDailyTopicsSchema:
    """Validate daily_topics[] structure per GUIDELINES.md Section 2.2"""

    REQUIRED_FIELDS = [
        "canonical_title", "summary_zh", "tags",
        "score_breakdown", "source_urls", "topic_id"
    ]

    def test_required_fields_present(self):
        topic = self._make_minimal_topic()
        for field in self.REQUIRED_FIELDS:
            assert field in topic, f"Missing required field: {field}"

    def test_score_breakdown_structure(self):
        topic = self._make_minimal_topic()
        breakdown = topic["score_breakdown"]
        for key in ("novelty", "impact", "credibility", "total"):
            assert key in breakdown
            assert isinstance(breakdown[key], (int, float))
            assert 0 <= breakdown[key] <= 10

    def test_topic_id_generation(self):
        title = "DeepSeek R2 发布"
        expected_hash = hashlib.sha1(title.encode()).hexdigest()[:8]
        today = date.today().strftime("%Y%m%d")
        topic = self._make_minimal_topic(title=title)
        assert topic["topic_id"] == f"{today}_{expected_hash}"

    @staticmethod
    def _make_minimal_topic(title="DeepSeek R2 发布"):
        today = date.today().strftime("%Y%m%d")
        hash_part = hashlib.sha1(title.encode()).hexdigest()[:8]
        return {
            "canonical_title": title,
            "summary_zh": "一句话中文摘要",
            "tags": ["AI", "LLM"],
            "score_breakdown": {
                "novelty": 8, "impact": 9, "credibility": 7, "total": 8.0
            },
            "source_urls": ["https://example.com"],
            "topic_id": f"{today}_{hash_part}",
        }


class TestMCPToolContract:
    """Validate MCP server exposes exactly the expected tools.

    Uses file-based parsing to avoid import-time side-effects from services/__init__.py.
    """

    ROOT = Path(__file__).resolve().parents[1]
    SERVER_PATH = ROOT / "opinion_mcp" / "server.py"

    EXPECTED_TOOLS = [
        "render_cards",
        "publish_xhs_note",
        "check_xhs_status",
        "get_xhs_login_qrcode",
        "check_xhs_login_session",
        "submit_xhs_verification",
    ]

    def _server_content(self) -> str:
        return self.SERVER_PATH.read_text(encoding="utf-8")

    def test_tool_count(self):
        """MCP server must declare exactly 6 MCPTool entries in TOOL_HANDLERS"""
        import re
        content = self._server_content()
        # TOOL_HANDLERS dict maps exactly one entry per tool; count its entries
        handlers_idx = content.index("TOOL_HANDLERS = {")
        handlers_end = content.index("}", handlers_idx)
        handlers_block = content[handlers_idx:handlers_end]
        entries = re.findall(r'"(\w+)":\s+\w+', handlers_block)
        assert len(entries) == 6, f"Expected 6 handler entries, got {len(entries)}: {entries}"

    def test_tool_names_match(self):
        """All 6 canonical tool names must appear as name=... in MCP_TOOLS"""
        content = self._server_content()
        for tool_name in self.EXPECTED_TOOLS:
            assert f'name="{tool_name}"' in content, (
                f"Tool name not found in server.py: {tool_name}"
            )

    def test_render_cards_schema(self):
        """render_cards block must declare specs as array type"""
        import re
        content = self._server_content()
        # Find the render_cards MCPTool block
        match = re.search(
            r'name="render_cards".*?MCPTool\(',
            content,
            re.DOTALL,
        )
        # Simpler: just verify "specs" and "type": "array" co-occur near render_cards
        render_idx = content.index('name="render_cards"')
        # Find next MCPTool after render_cards (boundary of next tool)
        next_tool_idx = content.find('MCPTool(', render_idx + 1)
        block = content[render_idx:next_tool_idx] if next_tool_idx != -1 else content[render_idx:]
        assert '"specs"' in block, "render_cards must declare 'specs' property"
        assert '"array"' in block, "render_cards specs must be type 'array'"

    def test_publish_xhs_note_no_job_id(self):
        """publish_xhs_note properties must NOT include job_id key"""
        content = self._server_content()
        publish_idx = content.index('name="publish_xhs_note"')
        next_tool_idx = content.find('MCPTool(', publish_idx + 1)
        block = content[publish_idx:next_tool_idx] if next_tool_idx != -1 else content[publish_idx:]
        # Check job_id does not appear as a quoted property key
        assert '"job_id"' not in block, "publish_xhs_note should not accept job_id as a property"
        assert '"title"' in block
        assert '"content"' in block
        assert '"images"' in block

    def test_tool_handlers_match_tools(self):
        """Every tool name must appear in the TOOL_HANDLERS dict"""
        content = self._server_content()
        # Locate TOOL_HANDLERS block
        handlers_idx = content.index("TOOL_HANDLERS = {")
        handlers_end = content.index("}", handlers_idx)
        handlers_block = content[handlers_idx:handlers_end]
        for tool_name in self.EXPECTED_TOOLS:
            assert f'"{tool_name}"' in handlers_block, (
                f"No handler mapping for tool: {tool_name}"
            )


class TestRenderCardsPayload:
    """Validate render_cards payload schemas per GUIDELINES.md Section 1.1"""

    VALID_CARD_TYPES = {
        "title", "verdict", "evidence", "delta", "action",
        "impact", "hot-topic", "daily-rank", "radar", "timeline"
    }

    def test_all_card_types_documented(self):
        """All valid card types should be recognized"""
        for ct in self.VALID_CARD_TYPES:
            payload = self._minimal_payload(ct)
            assert payload is not None, f"No minimal payload for card_type: {ct}"

    def test_title_card_required_fields(self):
        payload = self._minimal_payload("title")
        assert "title" in payload
        assert "emoji" in payload
        assert "theme" in payload

    def test_verdict_card_required_fields(self):
        payload = self._minimal_payload("verdict")
        for field in ("title", "verdict", "why_now", "confidence", "caveat", "stance", "tags"):
            assert field in payload, f"verdict card missing field: {field}"
        assert 0 <= payload["confidence"] <= 1

    def test_evidence_card_required_fields(self):
        payload = self._minimal_payload("evidence")
        for field in ("title", "entries", "takeaway", "tags"):
            assert field in payload, f"evidence card missing field: {field}"
        assert isinstance(payload["entries"], list)
        entry = payload["entries"][0]
        for field in ("claim", "detail", "source", "strength"):
            assert field in entry, f"evidence entry missing field: {field}"

    def test_delta_card_required_fields(self):
        payload = self._minimal_payload("delta")
        for field in ("title", "opening", "challenge", "revision", "resolution", "confidence"):
            assert field in payload, f"delta card missing field: {field}"
        assert 0 <= payload["confidence"] <= 1

    def test_action_card_required_fields(self):
        payload = self._minimal_payload("action")
        for field in ("title", "strategy", "actions", "watchouts", "audience", "tags"):
            assert field in payload, f"action card missing field: {field}"
        assert isinstance(payload["actions"], list)
        assert isinstance(payload["watchouts"], list)

    def test_impact_card_required_fields(self):
        payload = self._minimal_payload("impact")
        for field in ("title", "summary", "insight", "signals", "actions", "confidence", "tags"):
            assert field in payload, f"impact card missing field: {field}"
        assert isinstance(payload["signals"], list)
        assert isinstance(payload["actions"], list)
        assert 0 <= payload["confidence"] <= 1

    def test_hot_topic_card_required_fields(self):
        payload = self._minimal_payload("hot-topic")
        for field in ("title", "summary", "tags", "sourceCount", "score", "date"):
            assert field in payload, f"hot-topic card missing field: {field}"

    def test_daily_rank_card_required_fields(self):
        payload = self._minimal_payload("daily-rank")
        assert "date" in payload
        assert "topics" in payload
        assert "title" in payload
        assert isinstance(payload["topics"], list)
        topic = payload["topics"][0]
        for field in ("rank", "title", "score", "tags"):
            assert field in topic, f"daily-rank topic missing field: {field}"

    def test_radar_card_required_fields(self):
        payload = self._minimal_payload("radar")
        assert "labels" in payload
        assert "datasets" in payload
        assert isinstance(payload["labels"], list)
        assert isinstance(payload["datasets"], list)
        ds = payload["datasets"][0]
        assert "label" in ds
        assert "data" in ds

    def test_timeline_card_required_fields(self):
        payload = self._minimal_payload("timeline")
        assert "timeline" in payload
        assert isinstance(payload["timeline"], list)
        entry = payload["timeline"][0]
        for field in ("round", "title", "summary"):
            assert field in entry, f"timeline entry missing field: {field}"

    @staticmethod
    def _minimal_payload(card_type: str) -> dict:
        payloads = {
            "title": {"title": "测试标题", "emoji": "🔍", "theme": "warm"},
            "verdict": {
                "title": "标题",
                "verdict": "一句话判断",
                "why_now": "为什么现在值得讲",
                "confidence": 0.82,
                "caveat": "结论边界",
                "stance": "谨慎看多",
                "tags": ["#AI"],
            },
            "evidence": {
                "title": "标题",
                "entries": [{
                    "claim": "关键证据",
                    "detail": "支持了这条判断",
                    "source": "来源名",
                    "strength": "High",
                }],
                "takeaway": "证据整体说明什么",
                "tags": ["#AI"],
            },
            "delta": {
                "title": "标题",
                "opening": "初版判断",
                "challenge": "主要质疑",
                "revision": "修正结论",
                "resolution": "为何这样收束",
                "confidence": 0.78,
            },
            "action": {
                "title": "标题",
                "strategy": "一句话执行策略",
                "actions": ["先做一件事"],
                "watchouts": ["重点风险"],
                "audience": "个人用户",
                "tags": ["#AI"],
            },
            "impact": {
                "title": "标题", "summary": "摘要", "insight": "洞察",
                "signals": ["信号"],
                "actions": ["建议"], "confidence": 0.9, "tags": ["#AI"]
            },
            "hot-topic": {
                "title": "标题", "summary": "摘要", "tags": [],
                "sourceCount": 5, "score": 8.5, "date": "2025-01-01"
            },
            "daily-rank": {
                "date": "2025-01-01",
                "topics": [{"rank": 1, "title": "话题", "score": 9.0, "tags": ["AI"]}],
                "title": "AI 每日热点"
            },
            "radar": {
                "labels": ["维度1", "维度2"],
                "datasets": [{"label": "数据集", "data": [80, 60]}]
            },
            "timeline": {
                "timeline": [{"round": 1, "title": "第一轮", "summary": "关键转折"}]
            },
        }
        return payloads.get(card_type)
