import pytest
import httpx
import json

from app.services.xiaohongshu_publisher import XiaohongshuPublisher


async def _mcp_initialized_client() -> tuple[httpx.AsyncClient, dict[str, str]]:
    client = httpx.AsyncClient(timeout=30.0)
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    init_response = await client.post(
        "http://localhost:18060/mcp",
        headers=headers,
        json={
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest", "version": "1.0"},
            },
            "id": 1,
        },
    )
    session_id = init_response.headers.get("mcp-session-id")
    call_headers = dict(headers)
    if session_id:
        call_headers["Mcp-Session-Id"] = session_id
    await client.post(
        "http://localhost:18060/mcp",
        headers=call_headers,
        json={
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        },
    )
    return client, call_headers


@pytest.mark.asyncio
async def test_check_login_status_requires_explicit_logged_in_signal(
    monkeypatch: pytest.MonkeyPatch,
):
    publisher = XiaohongshuPublisher("http://example.test/mcp")

    async def fake_call_mcp(
        tool_name: str, arguments=None, timeout: float = 60.0, account=None
    ):
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

    async def fake_call_mcp(
        tool_name: str, arguments=None, timeout: float = 60.0, account=None
    ):
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

    async def fake_call_mcp(
        tool_name: str, arguments=None, timeout: float = 60.0, account=None
    ):
        if tool_name == "check_login_status":
            return {
                "success": True,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": '{"loggedIn": true, "message": "Logged in"}',
                        }
                    ]
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
    assert result["login_status"] is True
    assert "内容访问校验" in result["message"]


@pytest.mark.asyncio
async def test_custom_xhs_sidecar_exposes_legacy_publish_tool():
    client, headers = await _mcp_initialized_client()
    try:
        response = await client.post(
            "http://localhost:18060/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 9001,
            },
        )
    finally:
        await client.aclose()

    assert response.status_code == 200
    payload = XiaohongshuPublisher._parse_sse_response(response.text)
    assert payload is not None
    tools = payload["result"]["tools"]
    names = {tool["name"] for tool in tools}
    assert "xhs_publish_content" in names


@pytest.mark.asyncio
async def test_custom_xhs_sidecar_routes_legacy_publish_tool_call():
    client, headers = await _mcp_initialized_client()
    try:
        response = await client.post(
            "http://localhost:18060/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "xhs_publish_content",
                    "arguments": {},
                },
                "id": 9003,
            },
        )
    finally:
        await client.aclose()

    assert response.status_code == 200
    payload = XiaohongshuPublisher._parse_sse_response(response.text)
    assert payload is not None
    error = payload.get("error")
    assert not (error and error.get("code") == -32601)


@pytest.mark.asyncio
async def test_publish_content_surfaces_inner_publish_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    publisher = XiaohongshuPublisher("http://example.test/mcp")

    async def fake_is_available() -> bool:
        return True

    async def fake_check_login_status(account_id=None):
        return {"success": True, "logged_in": True, "message": "ok"}

    async def fake_call_mcp(
        tool_name: str, arguments=None, timeout: float = 60.0, account=None
    ):
        assert tool_name == "publish_content"
        return {
            "success": True,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "account": "demo-account",
                                "success": True,
                                "result": {
                                    "success": False,
                                    "error": "Publish button not found",
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

    result = await publisher.publish_content(
        title="测试标题",
        content="测试正文",
        images=["/tmp/test.png"],
    )

    assert result["success"] is False
    assert result["error"] == "Publish button not found"


@pytest.mark.asyncio
async def test_publish_content_surfaces_top_level_inner_failure(
    monkeypatch: pytest.MonkeyPatch,
):
    publisher = XiaohongshuPublisher("http://example.test/mcp")

    async def fake_is_available() -> bool:
        return True

    async def fake_check_login_status(account_id=None):
        return {"success": True, "logged_in": True, "message": "ok"}

    async def fake_call_mcp(
        tool_name: str, arguments=None, timeout: float = 60.0, account=None
    ):
        assert tool_name == "publish_content"
        return {
            "success": True,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "account": "demo-account",
                                "success": False,
                                "error": "CHECK constraint failed: note_type IN ('image', 'video')",
                            }
                        ),
                    }
                ]
            },
        }

    monkeypatch.setattr(publisher, "is_available", fake_is_available)
    monkeypatch.setattr(publisher, "check_login_status", fake_check_login_status)
    monkeypatch.setattr(publisher, "_call_mcp", fake_call_mcp)

    result = await publisher.publish_content(
        title="测试标题",
        content="测试正文",
        images=["/tmp/test.png"],
    )

    assert result["success"] is False
    assert result["error"] == "CHECK constraint failed: note_type IN ('image', 'video')"
