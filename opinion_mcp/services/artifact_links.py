from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional
from urllib.parse import urlencode

from opinion_mcp.services.account_context import get_account_id


def _get_public_api_base_url() -> str:
    configured = os.getenv("PUBLIC_API_BASE_URL", "").rstrip("/")
    if configured:
        return configured

    port = os.getenv("OPINION_MCP_PORT", "18061").strip() or "18061"
    return f"http://localhost:{port}"


def get_card_preview_public_base_url() -> str:
    return (
        os.getenv("CARD_PREVIEW_PUBLIC_BASE_URL", "").rstrip("/")
        or _get_public_api_base_url()
    )


def get_card_preview_output_dir(account_id: Optional[str] = None) -> Path:
    preview_dir = os.getenv("CARD_PREVIEW_OUTPUT_DIR", "outputs/card_previews")
    return (Path(preview_dir) / (account_id or get_account_id())).resolve()


def build_card_preview_route(filename: str, account_id: Optional[str] = None) -> str:
    safe_name = Path(filename).name
    acct = account_id or get_account_id()
    return f"/card-previews/{acct}/{safe_name}"


def build_card_preview_url(filename: str) -> str:
    return f"{get_card_preview_public_base_url()}{build_card_preview_route(filename)}"


def build_card_preview_gallery_route(filenames: Iterable[str], account_id: Optional[str] = None) -> Optional[str]:
    safe_names = [Path(filename).name for filename in filenames if filename]
    if not safe_names:
        return None
    acct = account_id or get_account_id()
    query = urlencode([("file", filename) for filename in safe_names] + [("account", acct)])
    return f"/card-previews/gallery?{query}"


def build_card_preview_gallery_url(filenames: Iterable[str]) -> Optional[str]:
    route = build_card_preview_gallery_route(filenames)
    if not route:
        return None
    return f"{get_card_preview_public_base_url()}{route}"


def resolve_card_preview_file_path(
    filename: str, account_id: Optional[str] = None
) -> Optional[Path]:
    output_dir = get_card_preview_output_dir(account_id=account_id)
    candidate = Path(filename)
    if candidate.name != filename:
        return None

    file_path = (output_dir / candidate.name).resolve()

    if file_path.parent != output_dir or not file_path.is_file():
        return None

    return file_path
