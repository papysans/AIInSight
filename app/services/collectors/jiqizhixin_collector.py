"""
机器之心 Collector (https://www.jiqizhixin.com/)
Scrapes AI news from Jiqizhixin using BeautifulSoup.
"""

import hashlib
import re
from typing import List
from loguru import logger

import httpx
from bs4 import BeautifulSoup
from app.schemas import SourceItem
from app.services.collectors import BaseCollector


class JiqizhixinCollector(BaseCollector):
    name = "jiqizhixin"
    source_type = "media"
    lang = "zh"
    base_url = "https://www.jiqizhixin.com"

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
            logger.info(f"[JiqizhixinCollector] Collected {len(items)} items")
        except Exception as e:
            logger.error(f"[JiqizhixinCollector] Failed: {e}")
        return items

    def _parse_html(self, html: str) -> List[SourceItem]:
        soup = BeautifulSoup(html, "lxml")
        article_pattern = re.compile(r"(?:/articles/|/daily/)")

        items: List[SourceItem] = []
        seen = set()
        for a_tag in soup.find_all("a", href=article_pattern):
            path = a_tag.get("href", "")
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 4 or path in seen:
                continue
            seen.add(path)
            url = f"{self.base_url}{path}" if path.startswith("/") else path
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


jiqizhixin_collector = JiqizhixinCollector()
