"""Tests for post-publish note_url recovery."""

import json

import pytest


@pytest.mark.asyncio
async def test_publish_note_url_from_noteId(monkeypatch):
    """publish_xhs_note should construct note_url from noteId."""
    from opinion_mcp.services.xiaohongshu_publisher import XiaohongshuPublisher
    from opinion_mcp.tools.publish import publish_xhs_note

    publisher = XiaohongshuPublisher("http://example.test/mcp")

    async def fake_is_available():
        return True

    async def fake_check_login_status(account_id=None):
        return {"success": True, "logged_in": True, "message": "ok"}

    async def fake_call_mcp(tool_name, arguments=None, timeout=60.0, account=None):
        return {
            "success": True,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "account": "demo",
                                "success": True,
                                "result": {
                                    "success": True,
                                    "noteId": "abc123def456",
                                },
                            }
                        ),
                    }
                ]
            },
        }

    monkeypatch.setattr(publisher, "is_available", fake_is_available)
    monkeypatch.setattr(publisher, "check_login_status", fake_check_login_status)
    monkeypatch.setattr(publisher, "_call_mcp", fake_call_mcp)

    # Monkey-patch the module-level singleton
    import opinion_mcp.tools.publish as pub_mod
    monkeypatch.setattr(pub_mod, "xiaohongshu_publisher", publisher)

    result = await publish_xhs_note(
        title="Test Title",
        content="Test content",
        images=["/tmp/test.png"],
    )

    assert result["success"] is True
    assert result["note_url"] == "https://www.xiaohongshu.com/explore/abc123def456"


@pytest.mark.asyncio
async def test_publish_note_url_null_shows_message(monkeypatch):
    """When no note_url can be recovered, should include explicit message."""
    from opinion_mcp.services.xiaohongshu_publisher import XiaohongshuPublisher
    from opinion_mcp.tools.publish import publish_xhs_note

    publisher = XiaohongshuPublisher("http://example.test/mcp")

    async def fake_is_available():
        return True

    async def fake_check_login_status(account_id=None):
        return {"success": True, "logged_in": True, "message": "ok"}

    async def fake_call_mcp(tool_name, arguments=None, timeout=60.0, account=None):
        return {
            "success": True,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps({"account": "demo", "success": True}),
                    }
                ]
            },
        }

    monkeypatch.setattr(publisher, "is_available", fake_is_available)
    monkeypatch.setattr(publisher, "check_login_status", fake_check_login_status)
    monkeypatch.setattr(publisher, "_call_mcp", fake_call_mcp)

    import opinion_mcp.tools.publish as pub_mod
    monkeypatch.setattr(pub_mod, "xiaohongshu_publisher", publisher)

    result = await publish_xhs_note(
        title="Test Title",
        content="Test content",
        images=["/tmp/test.png"],
    )

    assert result["success"] is True
    assert result["note_url"] is None
    assert "请在小红书 App 内查看" in result.get("message", "")
