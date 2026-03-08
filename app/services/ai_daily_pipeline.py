"""
AI Daily Pipeline
Orchestrates: multi-source collect → score → cluster → cache → return DailyTopics.
"""

import asyncio
from datetime import date, datetime
from typing import List, Optional
from loguru import logger

from app.config import settings
from app.schemas import SourceItem, DailyTopic, AiDailyResponse
from app.services.ai_daily_cache import ai_daily_cache
from app.services.ai_news_scorer import score_items
from app.services.ai_topic_cluster import cluster_source_items

# Collector registry
from app.services.collectors.aibase_collector import aibase_collector
from app.services.collectors.jiqizhixin_collector import jiqizhixin_collector
from app.services.collectors.qbitai_collector import qbitai_collector
from app.services.collectors.github_trending_collector import github_trending_collector
from app.services.collectors.producthunt_ai_collector import producthunt_ai_collector
from app.services.collectors.hf_papers_collector import hf_papers_collector
from app.services.collectors.techcrunch_ai_collector import techcrunch_ai_collector
from app.services.collectors.hn_collector import hn_collector
from app.services.collectors.reddit_collector import reddit_collector

ALL_COLLECTORS = {
    "aibase": aibase_collector,
    "jiqizhixin": jiqizhixin_collector,
    "qbitai": qbitai_collector,
    "github_trending": github_trending_collector,
    "producthunt_ai": producthunt_ai_collector,
    "hf_papers": hf_papers_collector,
    "techcrunch_ai": techcrunch_ai_collector,
    "hn": hn_collector,
    "reddit": reddit_collector,
}


async def _run_collectors(source_names: Optional[List[str]] = None) -> "tuple[List[SourceItem], List[str]]":
    """Run selected collectors in parallel. Returns (items, sources_used)."""
    config_sources = settings.AI_DAILY_CONFIG.get("sources", {})
    collectors_to_run = {}

    for name, collector in ALL_COLLECTORS.items():
        src_cfg = config_sources.get(name, {})
        if not src_cfg.get("enabled", True):
            continue
        if source_names and name not in source_names:
            continue
        collectors_to_run[name] = collector

    if not collectors_to_run:
        logger.warning("[AiDailyPipeline] No collectors to run")
        return [], []

    logger.info(f"[AiDailyPipeline] Running {len(collectors_to_run)} collectors: {list(collectors_to_run.keys())}")

    async def _safe_collect(name, collector):
        try:
            return name, await collector.collect()
        except Exception as e:
            logger.error(f"[AiDailyPipeline] Collector {name} failed: {e}")
            return name, []

    tasks = [_safe_collect(name, col) for name, col in collectors_to_run.items()]
    results = await asyncio.gather(*tasks)

    all_items: List[SourceItem] = []
    sources_used: List[str] = []
    for name, items in results:
        if items:
            all_items.extend(items)
            sources_used.append(name)

    logger.info(f"[AiDailyPipeline] Total raw items: {len(all_items)} from {len(sources_used)} sources")
    return all_items, sources_used


def _dedup_items(items: List[SourceItem]) -> List[SourceItem]:
    """De-duplicate by URL."""
    seen_urls = set()
    unique = []
    for item in items:
        if item.url not in seen_urls:
            seen_urls.add(item.url)
            unique.append(item)
    return unique


async def collect_ai_daily(
    force_refresh: bool = False,
    source_names: Optional[List[str]] = None,
) -> AiDailyResponse:
    """
    Main pipeline entry point.
    1. Check cache (unless force_refresh)
    2. Run collectors
    3. De-dup
    4. Score
    5. Cluster
    6. Cache
    7. Return
    """
    today = date.today()
    max_topics = settings.AI_DAILY_CONFIG.get("max_topics", 20)

    # Partial-source runs bypass cache to avoid serving/storing incomplete data
    use_cache = not source_names

    # 1. Cache hit
    if not force_refresh and use_cache:
        cached = ai_daily_cache.get(today)
        if cached:
            logger.info(f"[AiDailyPipeline] Cache hit for {today}")
            topics = [DailyTopic(**t) for t in cached.get("topics", [])]
            return AiDailyResponse(
                date=cached["date"],
                topics=topics,
                total=len(topics),
                sources_used=cached.get("sources_used", []),
                collected_at=cached.get("collected_at"),
            )

    # 2. Collect
    raw_items, sources_used = await _run_collectors(source_names)
    if not raw_items:
        return AiDailyResponse(date=today.isoformat(), topics=[], total=0, sources_used=[])

    # 3. Dedup
    items = _dedup_items(raw_items)
    logger.info(f"[AiDailyPipeline] After dedup: {len(items)} items")

    # 4. Score
    scored = score_items(items)

    # 4.5 Filter: drop items below AI relevance threshold
    AI_RELEVANCE_THRESHOLD = 3.0
    scored = [s for s in scored if s["ai_relevance_score"] >= AI_RELEVANCE_THRESHOLD]
    logger.info(f"[AiDailyPipeline] After relevance filter (>={AI_RELEVANCE_THRESHOLD}): {len(scored)} items")
    if not scored:
        return AiDailyResponse(date=today.isoformat(), topics=[], total=0, sources_used=sources_used)

    # 5. Cluster
    topics = cluster_source_items(scored, max_topics=max_topics)

    # 6. Cache (only full-source runs)
    if use_cache:
        ai_daily_cache.put(topics, sources_used, today)

    # 7. Return
    return AiDailyResponse(
        date=today.isoformat(),
        topics=topics,
        total=len(topics),
        sources_used=sources_used,
        collected_at=datetime.now().isoformat(),
    )


async def get_topic_by_id(topic_id: str) -> Optional[DailyTopic]:
    """Look up a single topic from today's cache."""
    cached = ai_daily_cache.get()
    if not cached:
        return None
    for t in cached.get("topics", []):
        if t.get("topic_id") == topic_id:
            return DailyTopic(**t)
    return None
