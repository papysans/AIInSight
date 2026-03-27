from pathlib import Path

from app.services.topic_card_builder import (
    build_topic_impact_payload,
    build_topic_radar_payload,
    build_topic_timeline,
)


def test_build_topic_radar_payload_groups_sources_by_source_group():
    payload = build_topic_radar_payload(
        source_stats={
            "aibase": 4,
            "jiqizhixin": 2,
            "hf_papers": 3,
            "github_trending": 1,
            "hn": 2,
        }
    )

    assert payload["labels"] == ["媒体", "研究", "开源", "社区"]
    assert payload["datasets"][0]["data"] == [50, 25, 8, 17]


def test_build_topic_timeline_parses_analyst_rounds_from_output_file(tmp_path: Path):
    output_file = tmp_path / "topic.md"
    output_file.write_text(
        """# Topic

## 最终文案

TITLE: 最终标题

---

## 辩论过程记录

### Analyst (Round 1)
SUMMARY: 第一轮摘要
INSIGHT: 第一轮洞察
TITLE: 第一轮标题
SUB: 第一轮副标题

### Debater (Critique Round 1)
质疑内容

### Analyst (Round 2)
SUMMARY: 第二轮摘要
INSIGHT: 第二轮洞察
TITLE: 第二轮标题
SUB: 第二轮副标题
""",
        encoding="utf-8",
    )

    timeline = build_topic_timeline(output_file=str(output_file))

    assert timeline == [
        {
            "round": 1,
            "title": "第一轮标题",
            "summary": "第一轮摘要",
            "insight": "第一轮洞察",
        },
        {
            "round": 2,
            "title": "第二轮标题",
            "summary": "第二轮摘要",
            "insight": "第二轮洞察",
        },
    ]


def test_build_topic_timeline_falls_back_to_summary_when_no_output_file():
    timeline = build_topic_timeline(
        title="核心判断",
        summary="这里是总结",
        insight="这里是洞察",
    )

    assert timeline == [
        {
            "round": 1,
            "title": "核心判断",
            "summary": "这里是总结",
            "insight": "这里是洞察",
        }
    ]


def test_build_topic_impact_payload_uses_groups_and_timeline():
    payload = build_topic_impact_payload(
        title="测试标题",
        summary="这是第一句。这里是第二句。",
        insight="这里是更深的洞察。",
        tags=["AI", "Agent"],
        source_stats={"aibase": 3, "github_trending": 2, "hn": 1},
        timeline=[
            {"round": 1, "title": "初始判断", "summary": "第一轮摘要"},
            {"round": 2, "title": "收敛结论", "summary": "第二轮摘要"},
        ],
    )

    assert payload["confidence"] == "高"
    assert payload["signals"][0] == "这是第一句"
    assert "媒体 / 开源" in payload["signals"][1]
    assert "初始判断" in payload["signals"][2]
    assert len(payload["actions"]) == 3
