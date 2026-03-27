"""Tests for _process_image() local-file-path normalization."""

import os
import tempfile

import pytest


@pytest.fixture
def shared_vol_env(monkeypatch, tmp_path):
    """Set up XHS_IMAGE_API_DIR and XHS_IMAGE_MCP_DIR pointing to temp dirs."""
    api_dir = tmp_path / "api_images"
    api_dir.mkdir()
    monkeypatch.setenv("XHS_IMAGE_API_DIR", str(api_dir))
    monkeypatch.setenv("XHS_IMAGE_MCP_DIR", "/app/images")
    return api_dir


def test_process_image_local_file_copies_to_shared_volume(shared_vol_env, tmp_path):
    """_process_image() with a local PNG file should copy to shared volume."""
    from opinion_mcp.services.xiaohongshu_publisher import _process_image

    # Create a fake local image file
    local_img = tmp_path / "card_preview.png"
    local_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    result = _process_image(str(local_img))

    # Should return an /app/images/... path
    assert result.startswith("/app/images/")
    assert result.endswith(".png")

    # The file should actually exist in the api_dir
    api_dir = shared_vol_env
    written_files = list(api_dir.iterdir())
    assert len(written_files) == 1
    assert written_files[0].read_bytes() == local_img.read_bytes()


def test_process_image_nonexistent_path_returns_unchanged():
    """_process_image() with a non-existent path should return it unchanged."""
    from opinion_mcp.services.xiaohongshu_publisher import _process_image

    bad_path = "/nonexistent/path/to/image.png"
    result = _process_image(bad_path)
    assert result == bad_path


def test_process_image_http_url_passes_through():
    """_process_image() with an HTTP URL should return it unchanged."""
    from opinion_mcp.services.xiaohongshu_publisher import _process_image

    url = "https://example.com/image.png"
    assert _process_image(url) == url


def test_process_image_data_url_writes_to_shared_volume(shared_vol_env):
    """_process_image() with a data URL should decode and write to shared volume."""
    import base64

    from opinion_mcp.services.xiaohongshu_publisher import _process_image

    raw_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
    data_url = f"data:image/png;base64,{base64.b64encode(raw_bytes).decode()}"

    result = _process_image(data_url)
    assert result.startswith("/app/images/")
    assert result.endswith(".png")

    api_dir = shared_vol_env
    written_files = list(api_dir.iterdir())
    assert len(written_files) == 1
