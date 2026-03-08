"""
Adapter: convert DailyTopic → GraphState input dict for the existing workflow.
"""

from typing import Dict, Any, List
from app.schemas import DailyTopic
from app.config import settings


def topic_to_workflow_input(topic: DailyTopic, depth: str = "standard") -> Dict[str, Any]:
    """
    Map an AI Daily topic into the GraphState expected by app_graph.ainvoke().

    Parameters
    ----------
    topic : DailyTopic
        Clustered topic from the AI Daily pipeline.
    depth : str
        "quick" / "standard" / "deep"
    """
    depth_cfg = settings.DEPTH_PRESETS.get(depth, settings.DEPTH_PRESETS["standard"])
    rounds = depth_cfg.get("debate_rounds", 2)

    # Build a rich topic string with context
    topic_text = topic.title
    if topic.summary_zh:
        topic_text += f"\n{topic.summary_zh}"

    # Build evidence_bundle from existing topic sources
    evidence_items = []
    source_stats: Dict[str, int] = {}
    for src in (topic.sources or []):
        evidence_items.append({
            "source_item": {
                "title": src.title,
                "url": src.url,
                "source": src.source,
                "summary": src.summary or "",
                "lang": src.lang or "en",
            },
            "full_text": src.summary or "",
            "extraction_status": "fallback",
        })
        source_stats[src.source] = source_stats.get(src.source, 0) + 1

    sources_analyzed = list(source_stats.keys())

    evidence_bundle = {
        "topic": topic_text,
        "items": evidence_items,
        "sources_analyzed": sources_analyzed,
        "skipped_sources": [],
        "source_stats": source_stats,
        "evidence_count": len(evidence_items),
        "from_cache": True,
    }

    return {
        "topic": topic_text,
        "source_groups": settings.DEFAULT_SOURCE_GROUPS,
        "source_names": None,
        "depth": depth,
        "debate_rounds": rounds,
        "image_count": 0,
        "evidence_bundle": evidence_bundle,
        "source_stats": source_stats,
        "news_content": "",
        "initial_analysis": "",
        "critique": None,
        "revision_count": 0,
        "final_copy": "",
        "image_urls": [],
        "dataview_images": [],
        "output_file": None,
        "messages": [],
        "debate_history": [],
        "safety_blocked": False,
        "safety_reason": None,
        "xhs_publish_enabled": False,
        "xhs_publish_result": None,
    }
