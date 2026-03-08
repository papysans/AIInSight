"""
AI Topic Cluster
Groups similar SourceItems into DailyTopics via title similarity.
"""

import hashlib
import re
from typing import List
from loguru import logger

from app.schemas import SourceItem, DailyTopic


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"[^\w\s]", "", text.lower().strip())


def _similarity(a: str, b: str) -> float:
    """Simple Jaccard similarity over character bigrams."""
    a_norm = _normalize(a)
    b_norm = _normalize(b)
    if not a_norm or not b_norm:
        return 0.0
    bigrams_a = {a_norm[i:i+2] for i in range(len(a_norm) - 1)}
    bigrams_b = {b_norm[i:i+2] for i in range(len(b_norm) - 1)}
    if not bigrams_a or not bigrams_b:
        return 0.0
    intersection = bigrams_a & bigrams_b
    union = bigrams_a | bigrams_b
    return len(intersection) / len(union)


def cluster_source_items(
    scored_items: List[dict],
    similarity_threshold: float = 0.35,
    max_topics: int = 20,
) -> List[DailyTopic]:
    """
    Cluster scored items into DailyTopics.

    Args:
        scored_items: list of dicts from ai_news_scorer.score_items()
        similarity_threshold: min Jaccard similarity to merge
        max_topics: max number of topics to return

    Returns:
        List of DailyTopic, sorted by final_score descending
    """
    clusters: List[dict] = []  # each cluster: {rep_title, items: [], scores: {}}

    for entry in scored_items:
        item: SourceItem = entry["item"]
        merged = False
        for cluster in clusters:
            if _similarity(item.title, cluster["rep_title"]) >= similarity_threshold:
                cluster["items"].append(entry)
                merged = True
                break
        if not merged:
            clusters.append({"rep_title": item.title, "items": [entry]})

    # Convert clusters to DailyTopics
    topics: List[DailyTopic] = []
    for cluster in clusters:
        entries = cluster["items"]
        # Use highest-scored item as representative
        entries.sort(key=lambda x: x["final_score"], reverse=True)
        best = entries[0]
        item: SourceItem = best["item"]

        # Collect all sources
        sources = [e["item"] for e in entries]
        all_tags = set()
        langs = set()
        for s in sources:
            all_tags.update(s.tags)
            langs.add(s.lang)

        topic_id = "cluster_" + hashlib.md5(item.title.encode()).hexdigest()[:12]

        # Average scores
        avg = lambda key: round(sum(e[key] for e in entries) / len(entries), 1)

        topics.append(DailyTopic(
            topic_id=topic_id,
            title=item.title,
            summary_zh=item.summary or item.title,
            sources=sources,
            tags=list(all_tags)[:10],
            source_count=len(sources),
            lang_mix=sorted(langs),
            ai_relevance_score=avg("ai_relevance_score"),
            impact_score=avg("impact_score"),
            freshness_score=avg("freshness_score"),
            discussion_score=avg("discussion_score"),
            final_score=avg("final_score"),
        ))

    topics.sort(key=lambda t: t.final_score, reverse=True)
    topics = topics[:max_topics]

    logger.info(f"[AiTopicCluster] {len(scored_items)} items -> {len(topics)} topics")
    return topics
