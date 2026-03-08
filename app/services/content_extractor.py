"""
Content Extractor Service
Extracts full-text content from URLs using trafilatura.
Concurrency-limited, with 3-state degradation.
"""

import asyncio
from typing import List, Optional

import httpx
from loguru import logger

from app.schemas import EvidenceItem, SourceItem

# trafilatura is sync; we run it in a thread pool.
try:
    import trafilatura
except ImportError:
    trafilatura = None  # type: ignore[assignment]
    logger.warning("[ContentExtractor] trafilatura not installed, extraction disabled")


_DEFAULT_CONCURRENCY = 5
_FETCH_TIMEOUT = 15


async def _fetch_html(client: httpx.AsyncClient, url: str) -> Optional[str]:
    """Fetch raw HTML from a URL."""
    try:
        resp = await client.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AIInSight/1.0)"},
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.debug(f"[ContentExtractor] fetch failed for {url}: {e}")
        return None


def _extract_text(html: str, url: str) -> Optional[str]:
    """Synchronous trafilatura extraction."""
    if not trafilatura:
        return None
    try:
        return trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
    except Exception as e:
        logger.debug(f"[ContentExtractor] trafilatura extract error: {e}")
        return None


class ContentExtractor:
    def __init__(self, concurrency: int = _DEFAULT_CONCURRENCY):
        self._semaphore = asyncio.Semaphore(concurrency)

    async def extract_one(self, source_item: SourceItem, client: httpx.AsyncClient) -> EvidenceItem:
        """Extract full text for a single SourceItem. Never raises."""
        async with self._semaphore:
            # Try trafilatura
            html_content = await _fetch_html(client, source_item.url)
            if html_content and trafilatura:
                loop = asyncio.get_running_loop()
                text = await loop.run_in_executor(None, _extract_text, html_content, source_item.url)
                if text and len(text.strip()) > 50:
                    return EvidenceItem(
                        source_item=source_item,
                        full_text=text.strip(),
                        extraction_status="success",
                    )

            # Fallback: use existing summary
            if source_item.summary:
                return EvidenceItem(
                    source_item=source_item,
                    full_text=source_item.summary,
                    extraction_status="fallback",
                )

            # Failed: keep title/URL only
            return EvidenceItem(
                source_item=source_item,
                full_text=None,
                extraction_status="failed",
            )

    async def extract_batch(self, items: List[SourceItem]) -> List[EvidenceItem]:
        """Extract full text for a batch of SourceItems concurrently."""
        if not items:
            return []

        async with httpx.AsyncClient(timeout=httpx.Timeout(_FETCH_TIMEOUT), follow_redirects=True) as client:
            tasks = [self.extract_one(item, client) for item in items]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        evidence: List[EvidenceItem] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"[ContentExtractor] Exception for {items[i].url}: {result}")
                evidence.append(EvidenceItem(
                    source_item=items[i],
                    full_text=None,
                    extraction_status="failed",
                ))
            else:
                evidence.append(result)

        stats = {"success": 0, "fallback": 0, "failed": 0}
        for e in evidence:
            stats[e.extraction_status] = stats.get(e.extraction_status, 0) + 1
        logger.info(f"[ContentExtractor] Batch done: {stats}")
        return evidence


content_extractor = ContentExtractor()
