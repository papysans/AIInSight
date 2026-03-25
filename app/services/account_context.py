from __future__ import annotations

from contextvars import ContextVar
from typing import Optional


_ACCOUNT_ID: ContextVar[str] = ContextVar("aiinsight_account_id", default="_default")


def set_account_id(account_id: Optional[str]) -> str:
    normalized = (account_id or "").strip() or "_default"
    _ACCOUNT_ID.set(normalized)
    return normalized


def get_account_id() -> str:
    return _ACCOUNT_ID.get()
