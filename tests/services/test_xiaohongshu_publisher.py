import pytest

from app.services.xiaohongshu_publisher import XiaohongshuPublisher


@pytest.mark.asyncio
async def test_check_login_status_requires_explicit_logged_in_signal(
    monkeypatch: pytest.MonkeyPatch,
):
    publisher = XiaohongshuPublisher("http://example.test/mcp")

    async def fake_call_mcp(tool_name: str, arguments=None, timeout: float = 60.0):
        assert tool_name == "check_login_status"
        return {"success": True, "result": {}}

    monkeypatch.setattr(publisher, "_call_mcp", fake_call_mcp)

    result = await publisher.check_login_status()

    assert result["success"] is True
    assert result["logged_in"] is False


@pytest.mark.asyncio
async def test_get_login_qrcode_uses_relaxed_default_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path
):
    monkeypatch.delenv("XHS_LOGIN_QRCODE_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setenv("XHS_LOGIN_QRCODE_DIR", str(tmp_path))
    publisher = XiaohongshuPublisher("http://example.test/mcp")
    captured: dict[str, float] = {}

    async def fake_call_mcp(tool_name: str, arguments=None, timeout: float = 60.0):
        assert tool_name == "get_login_qrcode"
        captured["timeout"] = timeout
        return {"success": False, "error": "请求超时，请稍后重试"}

    monkeypatch.setattr(publisher, "_call_mcp", fake_call_mcp)

    result = await publisher.get_login_qrcode()

    assert captured["timeout"] == 60.0
    assert result == {"success": False, "message": "请求超时，请稍后重试"}


@pytest.mark.asyncio
async def test_get_status_requires_authenticated_content_probe(
    monkeypatch: pytest.MonkeyPatch,
):
    publisher = XiaohongshuPublisher("http://example.test/mcp")

    async def fake_is_available() -> bool:
        return True

    async def fake_call_mcp(tool_name: str, arguments=None, timeout: float = 60.0):
        if tool_name == "check_login_status":
            return {
                "success": True,
                "result": {
                    "content": [{"type": "text", "text": "✅ 已登录\n用户名: demo"}]
                },
            }
        if tool_name == "list_feeds":
            return {
                "success": True,
                "result": {
                    "isError": True,
                    "content": [
                        {"type": "text", "text": "获取Feeds列表失败: login required"}
                    ],
                },
            }
        raise AssertionError(f"unexpected tool: {tool_name}")

    monkeypatch.setattr(publisher, "is_available", fake_is_available)
    monkeypatch.setattr(publisher, "_call_mcp", fake_call_mcp)

    result = await publisher.get_status()

    assert result["mcp_available"] is True
    assert result["login_status"] is False
    assert "内容访问校验" in result["message"]
