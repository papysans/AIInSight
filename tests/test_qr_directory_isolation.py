"""Tests for QR code directory account isolation."""

import os
from pathlib import Path

import pytest


def test_get_login_qrcode_dir_with_account_id(tmp_path, monkeypatch):
    """QR dir should include account_id subdirectory when provided."""
    from opinion_mcp.services.xiaohongshu_publisher import XiaohongshuPublisher

    monkeypatch.setenv("XHS_LOGIN_QRCODE_DIR", str(tmp_path / "xhs_login"))

    publisher = XiaohongshuPublisher("http://example.test/mcp")
    result = publisher._get_login_qrcode_dir(account_id="user123")

    assert "user123" in str(result)
    assert result.is_dir()


def test_get_login_qrcode_dir_without_account_id(tmp_path, monkeypatch):
    """QR dir should be the base directory when no account_id provided."""
    from opinion_mcp.services.xiaohongshu_publisher import XiaohongshuPublisher

    monkeypatch.setenv("XHS_LOGIN_QRCODE_DIR", str(tmp_path / "xhs_login"))

    publisher = XiaohongshuPublisher("http://example.test/mcp")
    result = publisher._get_login_qrcode_dir()

    assert "user123" not in str(result)
    assert result.is_dir()
