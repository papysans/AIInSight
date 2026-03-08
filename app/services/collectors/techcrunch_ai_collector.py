"""
TechCrunch AI Collector (https://techcrunch.com/category/artificial-intelligence/)
Scrapes AI articles from TechCrunch using BeautifulSoup.
Post-filters by AI relevance keywords to reduce noise.
"""

import hashlib
import re
from typing import List
from loguru import logger

import httpx
from bs4 import BeautifulSoup
from app.schemas import SourceItem
from app.services.collectors import BaseCollector

# Keywords that indicate genuine AI content (case-insensitive check)
_AI_SIGNAL_WORDS = {
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "gpt", "transformer", "neural", "openai", "anthropic",
    "deepseek", "gemini", "claude", "diffusion", "agent", "model",
    "chatbot", "copilot", "generative", "agi",
}


class TechcrunchAiCollector(BaseCollector):
    name = "techcrunch_ai"
    source_type = "media"
    lang = "en"
    base_url = "https://techcrunch.com"

    async def collect(self) -> List[SourceItem]:
        items: List[SourceItem] = []
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.base_url}/category/artificial-intelligence/",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) GlobalInSight/1.0"},
                )
                resp.raise_for_status()
                html = resp.text

            items = self._parse_html(html)
            logger.info(f"[TechcrunchAiCollector] Collected {len(items)} items")
        except Exception as e:
            logger.error(f"[TechcrunchAiCollector] Failed: {e}")
        return items

    @staticmethod
    def _is_ai_relevant(title: str) -> bool:
        """Check if the title contains at least one AI-related keyword."""
        lower = title.lower()
        return any(kw in lower for kw in _AI_SIGNAL_WORDS)

    def _parse_html(self, html: str) -> List[SourceItem]:
        soup = BeautifulSoup(html, "lxml")
        article_pattern = re.compile(
            r"^https://techcrunch\.com/\d{4}/\d{2}/\d{2}/[^/]+/?$"
        )

        items: List[SourceItem] = []
        seen = set()
        for a_tag in soup.find_all("a", href=article_pattern):
            url = a_tag["href"].rstrip("/")
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 5 or url in seen:
                continue
            # Post-filter: only keep AI-relevant articles
            if not self._is_ai_relevant(title):
                continue
            seen.add(url)
            item_id = hashlib.md5(url.encode()).hexdigest()[:16]
            items.append(
                SourceItem(
                    id=item_id,
                    title=title,
                    url=url,
                    source=self.name,
                    source_type=self.source_type,
                    lang=self.lang,
                    tags=["techcrunch", "ai"],
                )
            )
        return items


techcrunch_ai_collector = TechcrunchAiCollector()
