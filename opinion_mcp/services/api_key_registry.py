from __future__ import annotations

import json
import secrets
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List, Optional


class ApiKeyRegistry:
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or (Path("cache") / "api_keys.json")

    def _load(self) -> List[Dict[str, Any]]:
        if not self.storage_path.exists():
            return []
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8") or "[]")
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def _save(self, rows: List[Dict[str, Any]]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def create_key(self, account_id: str, note: str = "") -> Dict[str, Any]:
        rows = self._load()
        record = {
            "api_key": secrets.token_urlsafe(24),
            "account_id": account_id,
            "note": note,
            "status": "active",
            "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        rows.append(record)
        self._save(rows)
        return record

    def resolve_account_id(self, api_key: str) -> Optional[str]:
        for row in self._load():
            if row.get("api_key") == api_key and row.get("status") == "active":
                return row.get("account_id")
        return None

    def revoke_key(self, api_key: str) -> bool:
        rows = self._load()
        changed = False
        for row in rows:
            if row.get("api_key") == api_key and row.get("status") != "revoked":
                row["status"] = "revoked"
                changed = True
        if changed:
            self._save(rows)
        return changed

    def list_keys(self) -> List[Dict[str, Any]]:
        return [
            {
                "account_id": row.get("account_id"),
                "note": row.get("note", ""),
                "status": row.get("status", "active"),
                "created_at": row.get("created_at"),
            }
            for row in self._load()
        ]


api_key_registry = ApiKeyRegistry()
