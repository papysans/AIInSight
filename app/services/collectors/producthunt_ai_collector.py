"""
Product Hunt AI Collector (https://www.producthunt.com/topics/artificial-intelligence)
Scrapes AI products from Product Hunt using BeautifulSoup.
Note: Product Hunt heavily relies on client-side rendering; fallback to
structured data extraction from <script> tags when available.
"""

import hashlib
import json
import re
from typing import List
from loguru import logger

import httpx
from bs4 import BeautifulSoup
from app.schemas import SourceItem
from app.services.collectors import BaseCollector


class ProducthuntAiCollector(BaseCollector):
    name = "producthunt_ai"
    source_type = "product"
    lang = "en"
    base_url = "https://www.producthunt.com"

    async def collect(self) -> List[SourceItem]:
        items: List[SourceItem] = []
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.base_url}/topics/artificial-intelligence",
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) GlobalInSight/1.0",
                        "Accept": "text/html,application/xhtml+xml",
                    },
                )
                resp.raise_for_status()
                html = resp.text

            items = self._parse_html(html)
            logger.info(f"[ProducthuntAiCollector] Collected {len(items)} items")
        except Exception as e:
            logger.error(f"[ProducthuntAiCollector] Failed: {e}")
        return items

    def _parse_html(self, html: str) -> List[SourceItem]:
        soup = BeautifulSoup(html, "lxml")
        items: List[SourceItem] = []
        seen = set()

        # Strategy 1: Extract from <a href="/posts/..."> links
        post_pattern = re.compile(r"/posts/[a-zA-Z0-9_-]+$")
        for a_tag in soup.find_all("a", href=post_pattern):
            path = a_tag["href"]
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 3 or path in seen:
                continue
            seen.add(path)
            url = f"{self.base_url}{path}"
            item_id = hashlib.md5(url.encode()).hexdigest()[:16]
            items.append(
                SourceItem(
                    id=item_id, title=title, url=url,
                    source=self.name, source_type=self.source_type,
                    lang=self.lang, tags=["product", "ai"],
                )
            )

        # Strategy 2: Try JSON-LD / __NEXT_DATA__ as fallback
        if not items:
            items = self._parse_json_ld(soup)

        return items

    def _parse_json_ld(self, soup: BeautifulSoup) -> List[SourceItem]:
        """Try to extract product info from embedded JSON-LD or Next.js data."""
        items: List[SourceItem] = []
        for script in soup.find_all("script", type="application/json"):
            try:
                data = json.loads(script.string or "")
                # Walk common Next.js shapes
                props = data.get("props", {}).get("pageProps", {})
                posts = props.get("posts") or props.get("products") or []
                for p in posts[:30]:
                    name = p.get("name") or p.get("title", "")
                    slug = p.get("slug", "")
                    if not name or not slug:
                        continue
                    url = f"{self.base_url}/posts/{slug}"
                    item_id = hashlib.md5(url.encode()).hexdigest()[:16]
                    items.append(
                        SourceItem(
                            id=item_id, title=name, url=url,
                            source=self.name, source_type=self.source_type,
                            lang=self.lang,
                            summary=p.get("tagline", ""),
                            tags=["product", "ai"],
                        )
                    )
            except (json.JSONDecodeError, AttributeError):
                continue
        return items


producthunt_ai_collector = ProducthuntAiCollector()
