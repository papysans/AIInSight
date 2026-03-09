from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_login_qrcode_endpoint_returns_absolute_url_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("PUBLIC_API_BASE_URL", raising=False)
    monkeypatch.delenv("XHS_LOGIN_QRCODE_PUBLIC_BASE_URL", raising=False)
    monkeypatch.setenv("XHS_LOGIN_QRCODE_DIR", str(tmp_path))

    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    async def fake_get_login_qrcode():
        return {
            "success": True,
            "message": "请扫码登录",
            "qr_filename": "xhs-login-qrcode-test.png",
            "qr_image_path": str(tmp_path / "xhs-login-qrcode-test.png"),
            "expires_at": "2026-03-09T11:44:41",
        }

    monkeypatch.setattr(xiaohongshu_publisher, "get_login_qrcode", fake_get_login_qrcode)

    response = client.get("/api/xhs/login-qrcode")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["qr_image_route"] == "/api/xhs/login-qrcode/file/xhs-login-qrcode-test.png"
    assert data["qr_image_url"] == "http://testserver/api/xhs/login-qrcode/file/xhs-login-qrcode-test.png"


def test_publish_endpoint_uses_dedicated_qrcode_public_base(monkeypatch):
    monkeypatch.setenv("PUBLIC_API_BASE_URL", "https://api.example.com")
    monkeypatch.setenv("XHS_LOGIN_QRCODE_PUBLIC_BASE_URL", "https://static.example.com")

    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    async def fake_publish_content(title, content, images, tags=None):
        return {
            "success": False,
            "message": "❌ 未登录，请先扫码",
            "login_required": True,
            "qr_filename": "xhs-login-qrcode-publish.png",
            "qr_image_path": "/app/outputs/xhs_login/xhs-login-qrcode-publish.png",
            "expires_at": "2026-03-09T11:44:41",
            "login_qrcode": {
                "message": "请扫码登录",
            },
        }

    monkeypatch.setattr(xiaohongshu_publisher, "publish_content", fake_publish_content)

    response = client.post(
        "/api/xhs/publish",
        json={
            "title": "测试标题",
            "content": "测试内容",
            "images": ["/tmp/test.png"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["login_required"] is True
    assert data["qr_image_route"] == "/api/xhs/login-qrcode/file/xhs-login-qrcode-publish.png"
    assert data["qr_image_url"] == "https://static.example.com/api/xhs/login-qrcode/file/xhs-login-qrcode-publish.png"
    assert data["login_qrcode"]["qr_image_url"] == "https://static.example.com/api/xhs/login-qrcode/file/xhs-login-qrcode-publish.png"


def test_ai_daily_ranking_cards_returns_absolute_preview_urls(monkeypatch):
    monkeypatch.delenv("PUBLIC_API_BASE_URL", raising=False)
    monkeypatch.delenv("CARD_PREVIEW_PUBLIC_BASE_URL", raising=False)

    from app.services.publish import ai_daily_publish_service

    async def fake_generate_ai_daily_ranking_cards(limit, title=None, card_types=None):
        return {
            "success": True,
            "date": "2026-03-09",
            "limit": limit,
            "title": title or "AI 榜单",
            "cards": {
                "title": {
                    "success": True,
                    "output_path": "/app/outputs/card_previews/demo-title.png",
                },
                "daily-rank": {
                    "success": True,
                    "output_path": "/app/outputs/card_previews/demo-daily-rank.png",
                },
            },
        }

    monkeypatch.setattr(
        ai_daily_publish_service,
        "generate_ai_daily_ranking_cards",
        fake_generate_ai_daily_ranking_cards,
    )

    response = client.post("/api/ai-daily/ranking/cards", json={"limit": 10})

    assert response.status_code == 200
    data = response.json()
    assert data["cards"]["title"]["image_url"] == "http://testserver/api/card-previews/demo-title.png"
    assert data["cards"]["daily-rank"]["image_url"] == "http://testserver/api/card-previews/demo-daily-rank.png"
