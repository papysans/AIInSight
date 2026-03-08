"""
AI Daily Cache
Manages daily cache files under cache/ai_daily/YYYY-MM-DD.json
"""

import json
from datetime import date
from pathlib import Path
from typing import Optional, List
from loguru import logger

from app.config import settings
from app.schemas import DailyTopic


class AiDailyCache:
    def __init__(self):
        self.cache_dir = Path(settings.AI_DAILY_CONFIG["cache_dir"])
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, d: date) -> Path:
        return self.cache_dir / f"{d.isoformat()}.json"

    def get(self, d: Optional[date] = None) -> Optional[dict]:
        """Load cached daily data. Returns raw dict or None."""
        d = d or date.today()
        p = self._path(d)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[AiDailyCache] Failed to read {p}: {e}")
            return None

    def put(self, topics: List[DailyTopic], sources_used: List[str], d: Optional[date] = None) -> None:
        """Write daily cache."""
        d = d or date.today()
        from datetime import datetime

        data = {
            "date": d.isoformat(),
            "collected_at": datetime.now().isoformat(),
            "sources_used": sources_used,
            "total": len(topics),
            "topics": [t.model_dump() for t in topics],
        }
        p = self._path(d)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[AiDailyCache] Cached {len(topics)} topics -> {p.name}")
        except Exception as e:
            logger.error(f"[AiDailyCache] Failed to write {p}: {e}")

    def exists(self, d: Optional[date] = None) -> bool:
        d = d or date.today()
        return self._path(d).exists()


ai_daily_cache = AiDailyCache()
