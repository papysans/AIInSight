from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings


SOURCE_GROUP_ORDER = [
    ("media", "媒体"),
    ("research", "研究"),
    ("code", "开源"),
    ("community", "社区"),
]

ANALYST_ROUND_RE = re.compile(
    r"^### Analyst \(Round (\d+)\)\n(.*?)(?=^### |\Z)",
    re.MULTILINE | re.DOTALL,
)


def _source_to_group(source_name: str) -> Optional[str]:
    for group, sources in settings.SOURCE_GROUPS.items():
        if source_name in sources:
            return group
    return None


def build_topic_radar_payload(
    source_stats: Optional[Dict[str, int]] = None,
    fallback_sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    grouped_counts = {group: 0 for group, _ in SOURCE_GROUP_ORDER}

    for source_name, raw_count in (source_stats or {}).items():
        group = _source_to_group(source_name)
        if not group:
            continue
        try:
            count = max(int(raw_count), 0)
        except (TypeError, ValueError):
            continue
        grouped_counts[group] += count

    if not any(grouped_counts.values()):
        for source_name in fallback_sources or []:
            group = _source_to_group(source_name)
            if group:
                grouped_counts[group] += 1

    total = sum(grouped_counts.values())
    if total > 0:
        data = [
            round(grouped_counts[group] / total * 100)
            for group, _ in SOURCE_GROUP_ORDER
        ]
    else:
        data = [0 for _ in SOURCE_GROUP_ORDER]

    return {
        "labels": [label for _, label in SOURCE_GROUP_ORDER],
        "datasets": [
            {
                "label": "证据占比",
                "data": data,
            }
        ],
    }


def _extract_tagged_value(block: str, tag: str) -> str:
    pattern = re.compile(rf"^{re.escape(tag)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(block or "")
    return match.group(1).strip() if match else ""


def _truncate_text(text: str, limit: int = 96) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _normalize_timeline_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []

    for index, item in enumerate(items or [], start=1):
        if not isinstance(item, dict):
            continue
        round_num = item.get("round") or index
        title = str(item.get("title") or f"第 {round_num} 轮").strip()
        summary = str(item.get("summary") or item.get("insight") or "").strip()
        insight = str(item.get("insight") or "").strip()
        normalized.append(
            {
                "round": round_num,
                "title": _truncate_text(title, limit=28),
                "summary": _truncate_text(summary, limit=96),
                "insight": insight,
            }
        )

    return normalized[:8]


def parse_debate_timeline(output_file: Optional[str]) -> List[Dict[str, Any]]:
    if not output_file:
        return []

    path = Path(output_file)
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    timeline: List[Dict[str, Any]] = []

    for match in ANALYST_ROUND_RE.finditer(text):
        round_num = int(match.group(1))
        block = match.group(2).strip()
        title = _extract_tagged_value(block, "TITLE") or f"第 {round_num} 轮"
        summary = _extract_tagged_value(block, "SUMMARY")
        insight = _extract_tagged_value(block, "INSIGHT")
        if not summary:
            summary = insight or block.splitlines()[0].strip()

        timeline.append(
            {
                "round": round_num,
                "title": title,
                "summary": summary,
                "insight": insight,
            }
        )

    return _normalize_timeline_items(timeline)


def build_topic_timeline(
    *,
    output_file: Optional[str] = None,
    timeline: Optional[List[Dict[str, Any]]] = None,
    title: str = "",
    summary: str = "",
    insight: str = "",
) -> List[Dict[str, Any]]:
    normalized = _normalize_timeline_items(timeline or [])
    if normalized:
        return normalized

    parsed = parse_debate_timeline(output_file)
    if parsed:
        return parsed

    fallback_summary = summary or insight or title or "等待更多分析结果"
    fallback_title = title or "核心结论"
    return [
        {
            "round": 1,
            "title": _truncate_text(fallback_title, limit=28),
            "summary": _truncate_text(fallback_summary, limit=96),
            "insight": insight,
        }
    ]


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"[。！？!?；;\n]", text or "")
    return [part.strip() for part in parts if part.strip()]


def _dominant_source_groups(source_stats: Dict[str, int]) -> List[str]:
    grouped_counts = {group: 0 for group, _ in SOURCE_GROUP_ORDER}
    for source_name, raw_count in (source_stats or {}).items():
        group = _source_to_group(source_name)
        if not group:
            continue
        try:
            grouped_counts[group] += max(int(raw_count), 0)
        except (TypeError, ValueError):
            continue

    non_zero = [(group, count) for group, count in grouped_counts.items() if count > 0]
    non_zero.sort(key=lambda item: item[1], reverse=True)
    return [group for group, _ in non_zero[:2]]


def build_topic_impact_payload(
    *,
    title: str = "",
    summary: str = "",
    insight: str = "",
    tags: Optional[List[str]] = None,
    source_stats: Optional[Dict[str, int]] = None,
    timeline: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    summary_points = _split_sentences(summary)
    insight_points = _split_sentences(insight)
    lead_signal = summary_points[0] if summary_points else (insight_points[0] if insight_points else "这个话题值得继续跟。")

    groups = _dominant_source_groups(source_stats or {})
    group_to_label = {group: label for group, label in SOURCE_GROUP_ORDER}

    signals: List[str] = [_truncate_text(lead_signal, limit=48)]
    if groups:
        labels = [group_to_label[group] for group in groups if group in group_to_label]
        if labels:
            signals.append(_truncate_text(f"{' / '.join(labels)} 信号占比更高，说明讨论重心已经形成。", limit=48))

    timeline_items = _normalize_timeline_items(timeline or [])
    if len(timeline_items) >= 2:
        first_title = timeline_items[0]["title"]
        last_title = timeline_items[-1]["title"]
        signals.append(_truncate_text(f"观点从「{first_title}」收敛到「{last_title}」。", limit=48))
    elif insight_points:
        signals.append(_truncate_text(insight_points[0], limit=48))

    actions: List[str] = []
    if "research" in groups:
        actions.append("补 benchmark、论文细节和可复现实验。")
    if "code" in groups:
        actions.append("追仓库更新、issue 反馈和二次封装生态。")
    if "community" in groups:
        actions.append("看社区吐槽、真实使用反馈和风险点。")
    if "media" in groups:
        actions.append("核对官方发布、商业动作和合作对象。")

    if not actions:
        actions = [
            "先拆主结论，再补一条最强证据。",
            "跟发布节奏、产品动作和外部反馈。",
            "把争议点单独拎出来做下一条内容。",
        ]
    else:
        fallback_actions = [
            "补最强证据链，避免只有观点没有抓手。",
            "盯住官方动作、社区反馈和二次传播节点。",
            "把分歧点单独拆成下一条跟进内容。",
        ]
        for fallback in fallback_actions:
            if len(actions) >= 3:
                break
            if fallback not in actions:
                actions.append(fallback)

    confidence = "高"
    if len(timeline_items) <= 1:
        confidence = "中"
    if not (source_stats or {}):
        confidence = "低"

    return {
        "title": title,
        "summary": summary,
        "insight": insight,
        "signals": signals[:3],
        "actions": actions[:3],
        "confidence": confidence,
        "tags": (tags or [])[:4],
    }
