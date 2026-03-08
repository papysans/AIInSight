"""
Hugging Face Trending Papers Collector (https://huggingface.co/papers)
Scrapes trending AI research papers from HF using BeautifulSoup.
"""

import hashlib
import re
from typing import List
from loguru import logger

import httpx
from bs4 import BeautifulSoup
from app.schemas import SourceItem
from app.services.collectors import BaseCollector


class HfPapersCollector(BaseCollector):
    name = "hf_papers"
    source_type = "research"
    lang = "en"
    base_url = "https://huggingface.co"

    async def collect(self) -> List[SourceItem]:
        items: List[SourceItem] = []
        try:
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(
                    f"{self.base_url}/papers",
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) GlobalInSight/1.0"},
                )
                resp.raise_for_status()
                html = resp.text

            items = self._parse_html(html)
            logger.info(f"[HfPapersCollector] Collected {len(items)} items")
        except Exception as e:
            logger.error(f"[HfPapersCollector] Failed: {e}")
        return items

    def _parse_html(self, html: str) -> List[SourceItem]:
        soup = BeautifulSoup(html, "lxml")
        paper_pattern = re.compile(r"/papers/\d{4}\.\d{4,6}")

        items: List[SourceItem] = []
        seen = set()
        for a_tag in soup.find_all("a", href=paper_pattern):
            path = a_tag["href"]
            title = a_tag.get_text(strip=True)
            if not title or len(title) < 5 or path in seen:
                continue
            seen.add(path)

            # Extract arxiv id from path
            arxiv_match = re.search(r"(\d{4}\.\d{4,6})", path)
            arxiv_id = arxiv_match.group(1) if arxiv_match else ""

            url = f"{self.base_url}{path}"
            item_id = hashlib.md5(url.encode()).hexdigest()[:16]
            items.append(
                SourceItem(
                    id=item_id,
                    title=title,
                    url=url,
                    source=self.name,
                    source_type=self.source_type,
                    lang=self.lang,
                    tags=["paper", "research"],
                    extra={"arxiv_id": arxiv_id},
                )
            )
        return items


hf_papers_collector = HfPapersCollector()
