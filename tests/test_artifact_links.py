import pytest
import importlib

from opinion_mcp.services.account_context import set_account_id
from opinion_mcp.services.artifact_links import (
    build_card_preview_gallery_url,
    resolve_card_preview_file_path,
)
from opinion_mcp.tools.render import render_cards


def test_resolve_card_preview_file_path_rejects_escape(tmp_path, monkeypatch):
    preview_root = tmp_path / "card_previews"
    account_dir = preview_root / "_default"
    account_dir.mkdir(parents=True)
    expected = account_dir / "sample.png"
    expected.write_bytes(b"png")

    monkeypatch.setenv("CARD_PREVIEW_OUTPUT_DIR", str(preview_root))
    set_account_id("_default")

    assert resolve_card_preview_file_path("sample.png") == expected.resolve()
    assert resolve_card_preview_file_path("../sample.png") is None


@pytest.mark.asyncio
async def test_render_cards_returns_gallery_url(monkeypatch):
    class DummyClient:
        async def render(self, card_type, payload):
            return {
                "success": True,
                "output_path": f"/tmp/{card_type}.png",
                "image_url": f"http://localhost:18061/card-previews/{card_type}.png",
            }

    monkeypatch.setenv("PUBLIC_API_BASE_URL", "http://localhost:18061")
    set_account_id("_default")

    client_module = importlib.import_module("opinion_mcp.services.card_render_client")

    monkeypatch.setattr(client_module, "card_render_client", DummyClient())

    result = await render_cards(
        [
            {"card_type": "title", "payload": {"title": "封面"}},
            {"card_type": "impact", "payload": {"title": "结论"}},
        ]
    )

    assert result["gallery_url"] == build_card_preview_gallery_url(
        ["title.png", "impact.png"]
    )
