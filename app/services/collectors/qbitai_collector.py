"""
量子位 Collector (https://www.qbitai.com/)
Scrapes AI news from QbitAI using BeautifulSoup.
"""

import hashlib
import re
from typing import List
from loguru import logger

import httpx
from bs4 import BeautifulSoup
from app.schemas import SourceItem
from app.services.collectors import BaseCollector


class QbitaiCollector(BaseCollector):
    name = "qbitai"
    source_type = "media"
    lang = "zh"
    base_url = "https://www.qbitai.com"

    async def collect(self) -> List[SourceItem]:
        items: List[SourceItem] = []
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.base_url}/",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) GlobalInSight/1.0"},
                )
                resp.raise_for_status()
                html = resp.text

            items = self._parse_html(html)
            logger.info(f"[QbitaiCollector] Collected {len(items)} items")
        except Exception as e:
            logger.error(f"[QbitaiCollector] Failed: {e}")
        return items

    def _parse_html(self, html: str) -> List[SourceItem]:
        soup = BeautifulSoup(html, "lxml")
        article_pattern = re.compile(r"https?://www\.qbitai\.com/\d{4}/\d{2}/")

        items: List[SourceItem] = []
        seen = set()
        for a_tag in soup.find_all("a", href=article_pattern):
            url = a_tag["href"]
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 4 or url in seen:
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
                )
            )
        return items


qbitai_collector = QbitaiCollector()
