"""
Card Render Client
Proxy layer that calls the renderer service and returns image data.
Skill / API layer only talks to this client, never directly to the renderer.
"""

import base64
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import os

import httpx
from loguru import logger
from opinion_mcp.services.account_context import get_account_id

# Inline config (previously from app.config.settings)
_RENDERER_SERVICE_URL = os.getenv("RENDERER_SERVICE_URL", "http://renderer:3001")
_RENDERER_TIMEOUT = int(os.getenv("RENDERER_TIMEOUT", "30"))
_PREVIEW_OUTPUT_DIR = os.getenv("CARD_PREVIEW_OUTPUT_DIR", "outputs/card_previews")


class CardRenderClient:
    """HTTP client for the headless renderer service."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[int] = None):
        self.base_url = (base_url or _RENDERER_SERVICE_URL).rstrip("/")
        self.timeout = timeout or _RENDERER_TIMEOUT

    def _build_output_path(self, card_type: str, payload: dict) -> Path:
        output_dir = (
            Path(_PREVIEW_OUTPUT_DIR) / get_account_id()
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        card_key = card_type.replace("/", "_").replace("-", "_")
        context = str(payload.get("title") or payload.get("date") or card_key)
        digest = hashlib.sha1(context.encode("utf-8")).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return output_dir / f"{timestamp}_{card_key}_{digest}.png"

    def _persist_preview(self, card_type: str, payload: dict, result: dict) -> dict:
        if not result.get("success") or not result.get("image_data_url"):
            return result

        image_data_url = result["image_data_url"]
        if not image_data_url.startswith("data:") or "," not in image_data_url:
            return result

        header, encoded = image_data_url.split(",", 1)
        if ";base64" not in header:
            return result

        try:
            image_bytes = base64.b64decode(encoded)
            output_path = self._build_output_path(card_type, payload)
            output_path.write_bytes(image_bytes)
            result["output_path"] = str(output_path.resolve())
        except Exception as exc:
            logger.warning(
                f"[CardRenderClient] Failed to persist preview for {card_type}: {exc}"
            )

        return result

    async def render(self, card_type: str, payload: dict) -> dict:
        """
        Render a card via the renderer service.

        Args:
            card_type: "title" | "impact" | "radar" | "timeline" | "trend" | "daily_rank" | "hot_topic"
            payload: Data required by the specific renderer.

        Returns:
            dict with keys: success, image_data_url, image_url, width, height, mime_type
        """
        url = f"{self.base_url}/render/{card_type}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return self._persist_preview(card_type, payload, data)
        except httpx.ConnectError:
            logger.warning(
                f"[CardRenderClient] Renderer service unreachable at {self.base_url}"
            )
            return {"success": False, "error": "Renderer service unreachable"}
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[CardRenderClient] HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
            return {"success": False, "error": f"HTTP {e.response.status_code}"}
        except Exception as e:
            logger.error(f"[CardRenderClient] Unexpected error: {e}")
            return {"success": False, "error": str(e)}

    async def render_title(
        self,
        title: str,
        emoji: str = "🔍",
        theme: str = "warm",
        emoji_position: Optional[Dict] = None,
    ) -> dict:
        return await self.render(
            "title",
            {
                "title": title,
                "emoji": emoji,
                "theme": theme,
                "emojiPos": (emoji_position or {}).get("pos", "bottom-right"),
            },
        )

    async def render_impact(
        self,
        title: str,
        summary: str,
        insight: str,
        signals: List[str],
        actions: List[str],
        confidence: str = "",
        tags: Optional[List[str]] = None,
    ) -> dict:
        return await self.render(
            "impact",
            {
                "title": title,
                "summary": summary,
                "insight": insight,
                "signals": signals,
                "actions": actions,
                "confidence": confidence,
                "tags": tags or [],
            },
        )

    async def render_radar(self, labels: List[str], datasets: List[dict]) -> dict:
        return await self.render("radar", {"labels": labels, "datasets": datasets})

    async def render_timeline(self, timeline: List[dict]) -> dict:
        return await self.render("timeline", {"timeline": timeline})

    async def render_trend(self, stage: str, growth: int, curve: List[float]) -> dict:
        return await self.render(
            "trend", {"stage": stage, "growth": growth, "curve": curve}
        )

    async def render_daily_rank(
        self, date: Optional[str], topics: List[dict], title: str = "AI 每日热点"
    ) -> dict:
        from datetime import date as date_cls

        render_date = date or date_cls.today().isoformat()
        return await self.render(
            "daily_rank", {"date": render_date, "topics": topics, "title": title}
        )

    async def render_hot_topic(
        self,
        title: str,
        summary: str,
        tags: Optional[List[str]] = None,
        source_count: int = 0,
        score: float = 0.0,
        date: Optional[str] = None,
        sources: Optional[List[str]] = None,
    ) -> dict:
        from datetime import date as date_cls

        render_date = date or date_cls.today().isoformat()
        return await self.render(
            "hot_topic",
            {
                "title": title,
                "summary": summary,
                "tags": tags or [],
                "sourceCount": source_count,
                "score": score,
                "date": render_date,
                "sources": sources or [],
            },
        )

    async def is_available(self) -> bool:
        """Check if the renderer service is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/healthz")
                return resp.status_code == 200
        except Exception:
            return False


# Singleton
card_render_client = CardRenderClient()
