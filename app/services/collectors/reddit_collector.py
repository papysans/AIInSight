"""
Reddit Collector
- collect(): hot posts from AI-related subreddits for daily pipeline
- search(topic): Reddit search API for topic evidence retrieval
- Gracefully handles missing credentials (returns empty + warning)
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.schemas import SourceItem
from app.services.collectors import BaseCollector

AI_SUBREDDITS = [
    "artificial",
    "MachineLearning",
    "LocalLLaMA",
    "singularity",
    "ChatGPT",
]


class RedditCollector(BaseCollector):
    name = "reddit"
    source_type = "community"
    lang = "en"

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._lock = asyncio.Lock()

    def _has_credentials(self) -> bool:
        return bool(
            (os.getenv("REDDIT_CLIENT_ID") or "").strip()
            and (os.getenv("REDDIT_CLIENT_SECRET") or "").strip()
            and (os.getenv("REDDIT_USER_AGENT") or "").strip()
        )

    # ---------- BaseCollector: hot posts from AI subreddits ----------

    async def collect(self) -> List[SourceItem]:
        if not self._has_credentials():
            logger.warning("[RedditCollector] Missing Reddit credentials, skipping collect()")
            return []

        items: List[SourceItem] = []
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                for sub in AI_SUBREDDITS:
                    try:
                        posts = await self._fetch_subreddit_hot(client, sub, limit=10)
                        for post in posts:
                            item = self._post_to_source_item(post)
                            if item:
                                items.append(item)
                    except Exception as e:
                        logger.warning(f"[RedditCollector] Failed r/{sub}: {e}")
            logger.info(f"[RedditCollector] Collected {len(items)} items from {len(AI_SUBREDDITS)} subreddits")
        except Exception as e:
            logger.error(f"[RedditCollector] collect() failed: {e}")
        return items

    # ---------- Topic search ----------

    async def search(self, topic: str, max_items: int = 20, timeout: int = 30) -> List[SourceItem]:
        if not self._has_credentials():
            logger.warning("[RedditCollector] Missing Reddit credentials, skipping search()")
            return []

        items: List[SourceItem] = []
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                posts = await self._search_posts(client, topic, max_items)
                for post in posts:
                    item = self._post_to_source_item(post)
                    if item:
                        items.append(item)
            logger.info(f"[RedditCollector] search('{topic}') found {len(items)} items")
        except Exception as e:
            logger.error(f"[RedditCollector] search() failed: {e}")
        return items

    # ---------- OAuth ----------

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        async with self._lock:
            if self._token and time.time() < self._token_expires_at:
                return self._token

            client_id = (os.getenv("REDDIT_CLIENT_ID") or "").strip()
            client_secret = (os.getenv("REDDIT_CLIENT_SECRET") or "").strip()
            user_agent = (os.getenv("REDDIT_USER_AGENT") or "").strip()

            resp = await client.post(
                "https://www.reddit.com/api/v1/access_token",
                headers={"User-Agent": user_agent},
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Reddit OAuth failed: {resp.status_code} {resp.text}")

            payload = resp.json()
            token = (payload.get("access_token") or "").strip()
            if not token:
                raise RuntimeError(f"Reddit token missing: {payload}")

            self._token = token
            self._token_expires_at = time.time() + max(0, int(payload.get("expires_in") or 0) - 30)
            return token

    async def _api_get(
        self, client: httpx.AsyncClient, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        token = await self._get_token(client)
        user_agent = (os.getenv("REDDIT_USER_AGENT") or "").strip()
        headers = {"Authorization": f"bearer {token}", "User-Agent": user_agent, "Accept": "application/json"}
        url = f"https://oauth.reddit.com{path}"
        resp = await client.get(url, headers=headers, params=params)

        if resp.status_code == 401:
            async with self._lock:
                self._token = None
                self._token_expires_at = 0.0
            token = await self._get_token(client)
            headers["Authorization"] = f"bearer {token}"
            resp = await client.get(url, headers=headers, params=params)

        resp.raise_for_status()
        return resp.json()

    # ---------- Fetch helpers ----------

    async def _fetch_subreddit_hot(self, client: httpx.AsyncClient, subreddit: str, limit: int = 10) -> List[Dict]:
        data = await self._api_get(client, f"/r/{subreddit}/hot", params={"limit": str(limit), "raw_json": "1"})
        children = (((data or {}).get("data") or {}).get("children") or [])
        posts = []
        for child in children:
            if not isinstance(child, dict) or child.get("kind") != "t3":
                continue
            post = child.get("data") or {}
            if post.get("over_18") or post.get("stickied"):
                continue
            if post.get("id"):
                posts.append(post)
        return posts

    async def _search_posts(self, client: httpx.AsyncClient, keywords: str, max_items: int) -> List[Dict]:
        params = {
            "q": keywords,
            "limit": str(max_items),
            "sort": "relevance",
            "t": "week",
            "type": "link",
            "raw_json": "1",
        }
        data = await self._api_get(client, "/search", params=params)
        children = (((data or {}).get("data") or {}).get("children") or [])
        posts = []
        for child in children[:max_items]:
            if not isinstance(child, dict) or child.get("kind") != "t3":
                continue
            post = child.get("data") or {}
            if post.get("over_18"):
                continue
            if post.get("id"):
                posts.append(post)
        return posts

    # ---------- Standardize ----------

    @staticmethod
    def _post_to_source_item(post: Dict[str, Any]) -> Optional[SourceItem]:
        post_id = str(post.get("id") or "")
        title = (post.get("title") or "").strip()
        if not post_id or not title:
            return None
        permalink = (post.get("permalink") or "").strip()
        url = f"https://www.reddit.com{permalink}" if permalink else (post.get("url") or "")
        subreddit = post.get("subreddit") or ""
        return SourceItem(
            id=f"reddit_{post_id}",
            title=title,
            url=url,
            source="reddit",
            source_type="community",
            lang="en",
            summary=(post.get("selftext") or "")[:300] or None,
            tags=[f"r/{subreddit}"] if subreddit else [],
            extra={
                "score": int(post.get("ups") or 0),
                "num_comments": int(post.get("num_comments") or 0),
                "subreddit": subreddit,
                "author": post.get("author") or "",
            },
        )


reddit_collector = RedditCollector()
