"""
Topic Evidence Retriever
Core service replacing crawler_router_service.
Two-phase: cache search → realtime fetch → content extraction → EvidenceBundle.
"""

import asyncio
import json
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from app.config import settings
from app.schemas import EvidenceBundle, EvidenceItem, SourceItem

from app.services.content_extractor import content_extractor

# Collectors registry (search-capable and collect-only)
from app.services.collectors.hn_collector import hn_collector
from app.services.collectors.reddit_collector import reddit_collector

# Collect-only collectors (used via collect + filter)
from app.services.collectors.aibase_collector import aibase_collector
from app.services.collectors.jiqizhixin_collector import jiqizhixin_collector
from app.services.collectors.qbitai_collector import qbitai_collector
from app.services.collectors.github_trending_collector import github_trending_collector
from app.services.collectors.hf_papers_collector import hf_papers_collector
from app.services.collectors.techcrunch_ai_collector import techcrunch_ai_collector

# Search-capable collectors (have .search(topic) method)
_SEARCH_COLLECTORS = {
    "hn": hn_collector,
    "reddit": reddit_collector,
}

# Collect-only collectors (fetch latest, then filter by topic relevance)
_COLLECT_ONLY = {
    "aibase": aibase_collector,
    "jiqizhixin": jiqizhixin_collector,
    "qbitai": qbitai_collector,
    "github_trending": github_trending_collector,
    "hf_papers": hf_papers_collector,
    "techcrunch_ai": techcrunch_ai_collector,
}


def _resolve_sources(
    source_groups: Optional[List[str]] = None,
    source_names: Optional[List[str]] = None,
) -> List[str]:
    """Resolve which sources to query."""
    if source_names:
        return source_names

    groups = source_groups or settings.DEFAULT_SOURCE_GROUPS
    names: List[str] = []
    for g in groups:
        names.extend(settings.SOURCE_GROUPS.get(g, []))
    return names


def _topic_matches(item: SourceItem, keywords: List[str]) -> bool:
    """Simple keyword match against title + summary."""
    text = f"{item.title} {item.summary or ''}".lower()
    return any(kw in text for kw in keywords)


def _extract_keywords(topic: str) -> List[str]:
    """Extract search keywords from topic string."""
    # Split on common separators and keep meaningful tokens
    raw = re.sub(r'[，。！？、；：\u201c\u201d\u2018\u2019【】《》（）\s]+', ' ', topic.lower()).strip()
    tokens = [t for t in raw.split() if len(t) > 1]
    return tokens if tokens else [topic.lower()]


class TopicEvidenceRetriever:
    """Orchestrates evidence gathering for a topic analysis."""

    async def retrieve(
        self,
        topic: str,
        source_groups: Optional[List[str]] = None,
        source_names: Optional[List[str]] = None,
        depth: str = "standard",
    ) -> EvidenceBundle:
        """Main entry: gather evidence for a topic."""
        sources = _resolve_sources(source_groups, source_names)
        depth_cfg = settings.DEPTH_PRESETS.get(depth, settings.DEPTH_PRESETS["standard"])
        top_n = depth_cfg.get("top_n_extract", 10)
        min_items = settings.EVIDENCE_MIN_ITEMS

        logger.info(f"[EvidenceRetriever] topic='{topic}', sources={sources}, depth={depth}")

        # Phase 1: cache search
        cache_items = self._search_cache(topic)
        logger.info(f"[EvidenceRetriever] Cache hits: {len(cache_items)}")

        # Phase 2: realtime fetch (always, to supplement cache)
        realtime_items, sources_analyzed, skipped = await self._fetch_realtime(topic, sources)
        logger.info(f"[EvidenceRetriever] Realtime items: {len(realtime_items)}, skipped: {skipped}")

        # Merge and dedup
        all_items = self._dedup(cache_items + realtime_items)
        logger.info(f"[EvidenceRetriever] After dedup: {len(all_items)} items")

        # Phase 3: content extraction for top-N
        top_items = all_items[:top_n]
        evidence_items = await content_extractor.extract_batch(top_items)

        # Build remaining items as EvidenceItem with no extraction
        remaining = [
            EvidenceItem(source_item=item, full_text=None, extraction_status="skipped")
            for item in all_items[top_n:]
        ]
        all_evidence = evidence_items + remaining

        # Build source stats
        source_stats: Dict[str, int] = {}
        for e in all_evidence:
            src = e.source_item.source
            source_stats[src] = source_stats.get(src, 0) + 1

        bundle = EvidenceBundle(
            topic=topic,
            items=all_evidence,
            sources_analyzed=sources_analyzed,
            skipped_sources=skipped,
            source_stats=source_stats,
            evidence_count=len(all_evidence),
            from_cache=len(cache_items) > 0 and len(realtime_items) == 0,
        )
        logger.info(f"[EvidenceRetriever] Bundle: {bundle.evidence_count} items, stats={source_stats}")
        return bundle

    # ---------- Phase 1: Cache search ----------

    def _search_cache(self, topic: str) -> List[SourceItem]:
        """Scan recent AI daily cache files for matching items."""
        keywords = _extract_keywords(topic)
        cache_dir = Path(settings.AI_DAILY_CONFIG.get("cache_dir", "cache/ai_daily"))
        if not cache_dir.exists():
            return []

        search_days = settings.EVIDENCE_CACHE_SEARCH_DAYS
        today = date.today()
        items: List[SourceItem] = []
        seen_urls: Set[str] = set()

        for delta in range(search_days):
            d = today - timedelta(days=delta)
            p = cache_dir / f"{d.isoformat()}.json"
            if not p.exists():
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for topic_data in data.get("topics", []):
                    for src in topic_data.get("sources", []):
                        try:
                            si = SourceItem(**src)
                            if si.url not in seen_urls and _topic_matches(si, keywords):
                                seen_urls.add(si.url)
                                items.append(si)
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"[EvidenceRetriever] Cache read error {p}: {e}")

        return items

    # ---------- Phase 2: Realtime fetch ----------

    async def _fetch_realtime(
        self, topic: str, sources: List[str]
    ) -> tuple[List[SourceItem], List[str], List[str]]:
        """Fetch from all selected sources in parallel."""
        keywords = _extract_keywords(topic)
        timeout = settings.SOURCE_TIMEOUT_SECONDS

        async def _run_source(name: str) -> tuple[str, List[SourceItem], Optional[str]]:
            """Returns (name, items, error_or_none)."""
            try:
                if name in _SEARCH_COLLECTORS:
                    collector = _SEARCH_COLLECTORS[name]
                    results = await asyncio.wait_for(
                        collector.search(topic, max_items=20, timeout=timeout),
                        timeout=timeout + 5,
                    )
                    return (name, results, None)
                elif name in _COLLECT_ONLY:
                    collector = _COLLECT_ONLY[name]
                    all_items = await asyncio.wait_for(
                        collector.collect(),
                        timeout=timeout + 5,
                    )
                    # Filter by topic relevance
                    matched = [i for i in all_items if _topic_matches(i, keywords)]
                    return (name, matched, None)
                else:
                    return (name, [], f"Unknown source: {name}")
            except asyncio.TimeoutError:
                return (name, [], "timeout")
            except Exception as e:
                return (name, [], str(e))

        tasks = [_run_source(name) for name in sources]
        results = await asyncio.gather(*tasks)

        all_items: List[SourceItem] = []
        sources_analyzed: List[str] = []
        skipped: List[str] = []

        for name, items, error in results:
            if error:
                logger.warning(f"[EvidenceRetriever] Source '{name}' failed: {error}")
                skipped.append(name)
            else:
                sources_analyzed.append(name)
                all_items.extend(items)

        return all_items, sources_analyzed, skipped

    # ---------- Dedup ----------

    @staticmethod
    def _dedup(items: List[SourceItem]) -> List[SourceItem]:
        seen: Set[str] = set()
        unique: List[SourceItem] = []
        for item in items:
            if item.url not in seen:
                seen.add(item.url)
                unique.append(item)
        return unique


topic_evidence_retriever = TopicEvidenceRetriever()
