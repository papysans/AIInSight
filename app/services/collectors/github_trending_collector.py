"""
GitHub Trending Collector (https://github.com/trending)
Scrapes trending repositories from GitHub using BeautifulSoup.
"""

import hashlib
from typing import List
from loguru import logger

import httpx
from bs4 import BeautifulSoup
from app.schemas import SourceItem
from app.services.collectors import BaseCollector


class GithubTrendingCollector(BaseCollector):
    name = "github_trending"
    source_type = "code"
    lang = "en"
    base_url = "https://github.com"

    async def collect(self) -> List[SourceItem]:
        items: List[SourceItem] = []
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.base_url}/trending",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) GlobalInSight/1.0"},
                )
                resp.raise_for_status()
                html = resp.text

            items = self._parse_html(html)
            logger.info(f"[GithubTrendingCollector] Collected {len(items)} items")
        except Exception as e:
            logger.error(f"[GithubTrendingCollector] Failed: {e}")
        return items

    def _parse_html(self, html: str) -> List[SourceItem]:
        soup = BeautifulSoup(html, "lxml")
        items: List[SourceItem] = []
        seen = set()

        for article in soup.select("article.Box-row"):
            h2 = article.select_one("h2")
            if not h2:
                continue
            a_tag = h2.find("a")
            if not a_tag or not a_tag.get("href"):
                continue
            path = a_tag["href"].strip()
            if path in seen:
                continue
            seen.add(path)

            repo_name = path.lstrip("/")
            url = f"{self.base_url}{path}"

            # Description
            desc_el = article.select_one("p")
            summary = desc_el.get_text(strip=True) if desc_el else ""

            item_id = hashlib.md5(url.encode()).hexdigest()[:16]
            items.append(
                SourceItem(
                    id=item_id,
                    title=repo_name,
                    url=url,
                    source=self.name,
                    source_type=self.source_type,
                    lang=self.lang,
                    summary=summary,
                    tags=["github", "trending"],
                )
            )
        return items


github_trending_collector = GithubTrendingCollector()
