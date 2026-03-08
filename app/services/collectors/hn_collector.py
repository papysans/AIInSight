"""
Hacker News Collector
- collect(): top stories for AI daily pipeline
- search(topic): Algolia keyword search for topic evidence retrieval
"""

import asyncio
import hashlib
import html
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger

from app.schemas import SourceItem
from app.services.collectors import BaseCollector

_TAG_RE = re.compile(r"<[^>]+>")
_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_SPACE_RE = re.compile(r"\s+")

_HN_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for",
    "with", "about", "latest", "new", "news", "trend", "trends",
    "analysis", "overview", "update", "updates", "report", "insight",
}


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = _TAG_RE.sub("", text)
    return text.replace("\r", "").strip()


def _build_queries(keywords: str) -> List[str]:
    """Build fallback keyword queries for Algolia search."""
    raw = _SPACE_RE.sub(" ", (keywords or "").strip())
    if not raw:
        return []
    queries: List[str] = [raw]
    words = [w for w in _WORD_RE.findall(raw) if w]
    lowered = [w.lower() for w in words]
    kept = [w for w, lw in zip(words, lowered) if lw not in _HN_STOPWORDS]

    if len(words) >= 3:
        proper_nouns = [w for w in words if w[0].isupper() and len(w) > 1]
        if proper_nouns:
            queries.append(" ".join(proper_nouns[:5]))
        if kept:
            condensed = " ".join(kept[:8])
            if condensed.lower() != raw.lower():
                queries.append(condensed)

    seen: set[str] = set()
    out: List[str] = []
    for q in queries:
        q2 = _SPACE_RE.sub(" ", (q or "").strip())
        if not q2:
            continue
        key = q2.lower()
        if key not in seen:
            seen.add(key)
            out.append(q2)
    return out


class HNCollector(BaseCollector):
    name = "hn"
    source_type = "community"
    lang = "en"

    # ---------- BaseCollector: collect top stories for daily pipeline ----------

    async def collect(self) -> List[SourceItem]:
        """Fetch HN top stories (no keyword needed)."""
        items: List[SourceItem] = []
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
                resp.raise_for_status()
                story_ids = (resp.json() or [])[:30]

                sem = asyncio.Semaphore(10)

                async def fetch(sid: int) -> Optional[Dict[str, Any]]:
                    async with sem:
                        try:
                            r = await client.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                            r.raise_for_status()
                            return r.json()
                        except Exception:
                            return None

                results = await asyncio.gather(*[fetch(sid) for sid in story_ids])

                for data in results:
                    if not data or data.get("type") != "story":
                        continue
                    title = (data.get("title") or "").strip()
                    if not title:
                        continue
                    story_id = str(data.get("id") or "")
                    url = (data.get("url") or "").strip()
                    if not url:
                        url = f"https://news.ycombinator.com/item?id={story_id}"
                    items.append(SourceItem(
                        id=f"hn_{story_id}",
                        title=title,
                        url=url,
                        source="hn",
                        source_type="community",
                        lang="en",
                        summary=f"Points: {data.get('score', 0)} | Comments: {data.get('descendants', 0)}",
                        extra={
                            "points": data.get("score", 0),
                            "num_comments": data.get("descendants", 0),
                            "author": data.get("by", ""),
                            "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                        },
                    ))
            logger.info(f"[HNCollector] Collected {len(items)} top stories")
        except Exception as e:
            logger.error(f"[HNCollector] collect() failed: {e}")
        return items

    # ---------- Topic search via Algolia ----------

    async def search(self, topic: str, max_items: int = 20, timeout: int = 30) -> List[SourceItem]:
        """Search HN via Algolia for topic-related stories."""
        queries = _build_queries(topic)
        if not queries:
            return []

        items: List[SourceItem] = []
        seen_ids: set[str] = set()

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                for query in queries:
                    if len(items) >= max_items:
                        break

                    rel_hits, rec_hits = await asyncio.gather(
                        self._algolia_fetch(client, "search", query, max_items),
                        self._algolia_fetch(client, "search_by_date", query, max_items),
                    )

                    ranked = self._blend_rank(rel_hits, rec_hits)

                    for story_data in ranked:
                        if len(items) >= max_items:
                            break
                        story_id = str(story_data.get("objectID") or "").strip()
                        if not story_id or story_id in seen_ids:
                            continue
                        seen_ids.add(story_id)

                        title = (story_data.get("title") or "").strip()
                        if not title:
                            continue
                        url = (story_data.get("url") or "").strip()
                        if not url:
                            url = f"https://news.ycombinator.com/item?id={story_id}"
                        points = int(story_data.get("points") or 0)
                        num_comments = int(story_data.get("num_comments") or 0)

                        items.append(SourceItem(
                            id=f"hn_{story_id}",
                            title=title,
                            url=url,
                            source="hn",
                            source_type="community",
                            lang="en",
                            summary=f"Points: {points} | Comments: {num_comments}",
                            extra={
                                "points": points,
                                "num_comments": num_comments,
                                "author": story_data.get("author") or "",
                                "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                            },
                        ))

            logger.info(f"[HNCollector] search('{topic}') found {len(items)} items")
        except Exception as e:
            logger.error(f"[HNCollector] search() failed: {e}")
        return items

    async def _algolia_fetch(
        self, client: httpx.AsyncClient, endpoint: str, query: str, max_items: int
    ) -> List[Dict[str, Any]]:
        url = f"https://hn.algolia.com/api/v1/{endpoint}"
        hits: List[Dict[str, Any]] = []
        page = 0
        target = max(max_items, int(max_items * 1.5))
        while len(hits) < target and page < 5:
            params = {"query": query, "tags": "story", "hitsPerPage": str(min(100, target)), "page": str(page)}
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json() or {}
            page_hits = data.get("hits") or []
            if not page_hits:
                break
            hits.extend(page_hits)
            page += 1
            if page >= (data.get("nbPages") or 1):
                break
        return hits

    @staticmethod
    def _blend_rank(rel_hits: List[Dict], rec_hits: List[Dict]) -> List[Dict]:
        rel_rank: Dict[str, int] = {}
        for i, h in enumerate(rel_hits):
            sid = str(h.get("objectID") or "").strip()
            if sid and sid not in rel_rank:
                rel_rank[sid] = i
        rec_rank: Dict[str, int] = {}
        for i, h in enumerate(rec_hits):
            sid = str(h.get("objectID") or "").strip()
            if sid and sid not in rec_rank:
                rec_rank[sid] = i

        hit_by_id: Dict[str, Dict] = {}
        for h in rec_hits:
            sid = str(h.get("objectID") or "").strip()
            if sid:
                hit_by_id[sid] = h
        for h in rel_hits:
            sid = str(h.get("objectID") or "").strip()
            if sid:
                hit_by_id[sid] = h

        combined: List[Tuple[float, Dict]] = []
        for sid in set(rel_rank) | set(rec_rank):
            hit = hit_by_id.get(sid)
            if not hit:
                continue
            score = 0.0
            rr = rel_rank.get(sid)
            nr = rec_rank.get(sid)
            if rr is not None:
                score += 0.55 / (1.0 + rr)
            if nr is not None:
                score += 0.45 / (1.0 + nr)
            combined.append((score, hit))
        combined.sort(key=lambda x: x[0], reverse=True)
        return [h for _, h in combined]


hn_collector = HNCollector()
