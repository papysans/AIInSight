import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from typing import Optional, Dict, Any
from loguru import logger
from app.schemas import (
    XhsPublishRequest,
    XhsLoginQrcodeResponse,
    XhsUploadCookiesRequest,
    XhsUploadCookiesResponse,
    TitleCardRenderRequest,
    RadarCardRenderRequest,
    TimelineCardRenderRequest,
    TrendCardRenderRequest,
    ImpactCardRenderRequest,
    DailyRankCardRenderRequest,
    HotTopicCardRenderRequest,
    CardRenderResponse,
)
from app.config import settings
from app.services.account_context import get_account_id
from pathlib import Path


router = APIRouter()


def _get_public_api_base_url() -> str:
    return os.getenv("PUBLIC_API_BASE_URL", "").rstrip("/")


def _build_public_file_urls(
    request: Request,
    route_name: str,
    filename: str,
    public_base: str = "",
) -> tuple[str, str]:
    file_url = request.url_for(route_name, filename=filename)
    route = file_url.path
    if public_base:
        return route, f"{public_base}{route}"
    return route, str(file_url)


def _get_xhs_qrcode_public_base_url() -> str:
    return (
        os.getenv("XHS_LOGIN_QRCODE_PUBLIC_BASE_URL", "").rstrip("/")
        or _get_public_api_base_url()
    )


def _build_xhs_qrcode_urls(request: Request, filename: str) -> tuple[str, str]:
    return _build_public_file_urls(
        request=request,
        route_name="get_xhs_login_qrcode_file",
        filename=filename,
        public_base=_get_xhs_qrcode_public_base_url(),
    )


def _get_card_preview_public_base_url() -> str:
    return (
        os.getenv("CARD_PREVIEW_PUBLIC_BASE_URL", "").rstrip("/")
        or _get_public_api_base_url()
    )


def _get_card_preview_output_dir() -> Path:
    preview_dir = settings.AI_DAILY_CONFIG.get("preview_output_dir")
    preview_dir_str = (
        preview_dir
        if isinstance(preview_dir, str) and preview_dir
        else "outputs/card_previews"
    )
    return (Path(preview_dir_str) / get_account_id()).resolve()


def _build_card_preview_urls(request: Request, filename: str) -> tuple[str, str]:
    return _build_public_file_urls(
        request=request,
        route_name="get_card_preview_file",
        filename=filename,
        public_base=_get_card_preview_public_base_url(),
    )


def _enrich_card_render_result(
    request: Request, result: Dict[str, Any]
) -> Dict[str, Any]:
    enriched = dict(result)
    output_path = enriched.get("output_path")
    if not output_path:
        return enriched

    filename = Path(output_path).name
    _, image_url = _build_card_preview_urls(request, filename)
    enriched["image_url"] = image_url
    return enriched


def _enrich_xhs_publish_result(
    request: Request, result: Dict[str, Any]
) -> Dict[str, Any]:
    enriched = dict(result)
    qr_filename = enriched.get("qr_filename")
    if qr_filename:
        qr_route, qr_url = _build_xhs_qrcode_urls(request, qr_filename)
        enriched["qr_image_route"] = qr_route
        enriched["qr_image_url"] = qr_url

        login_qrcode = enriched.get("login_qrcode")
        if isinstance(login_qrcode, dict):
            login_qrcode = dict(login_qrcode)
            login_qrcode["qr_image_route"] = qr_route
            login_qrcode["qr_image_url"] = qr_url
            enriched["login_qrcode"] = login_qrcode
    return enriched


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "aiinsight-backend"}


# --- 小红书 MCP 发布接口 ---


@router.get("/xhs/status")
async def get_xhs_status(account_id: Optional[str] = None):
    """检查小红书 MCP 服务状态和登录状态"""
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher
    from app.schemas import XhsStatusResponse

    status = await xiaohongshu_publisher.get_status(account_id=account_id)
    return XhsStatusResponse(
        mcp_available=status.get("mcp_available", False),
        login_status=status.get("login_status", False),
        message=status.get("message", ""),
    )


@router.get("/xhs/login-qrcode", response_model=XhsLoginQrcodeResponse)
async def get_xhs_login_qrcode(request: Request, account_id: Optional[str] = None):
    """生成并返回小红书登录二维码信息。"""
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    result = await xiaohongshu_publisher.get_login_qrcode(account_id=account_id)

    if result.get("already_logged_in"):
        return XhsLoginQrcodeResponse(
            success=True,
            message=result.get("message", "已登录，无需扫码"),
            login_method="xhs-mcp",
        )

    if not result.get("success"):
        return XhsLoginQrcodeResponse(
            success=False,
            message=result.get("message", "获取登录二维码失败"),
        )

    qr_filename = result.get("qr_filename", "")
    qr_route, qr_url = _build_xhs_qrcode_urls(request, qr_filename)

    preview_base = _get_xhs_qrcode_public_base_url()
    preview_route = "/api/xhs/login-qrcode/preview"
    qr_preview_url = (
        f"{preview_base}{preview_route}"
        if preview_base
        else str(request.url_for("preview_xhs_login_qrcode"))
    )

    return XhsLoginQrcodeResponse(
        success=True,
        message=result.get("message", "请使用小红书 App 扫码登录"),
        qr_image_url=qr_url,
        qr_image_route=qr_route,
        qr_image_path=result.get("qr_image_path"),
        qr_preview_url=qr_preview_url,
        qr_ascii=result.get("qr_ascii"),
        expires_at=result.get("expires_at"),
        session_id=result.get("session_id"),
    )


@router.get("/xhs/login-qrcode/file/{filename}", name="get_xhs_login_qrcode_file")
async def get_xhs_login_qrcode_file(filename: str):
    """返回登录二维码图片文件。"""
    output_dir = (
        Path(os.getenv("XHS_LOGIN_QRCODE_DIR", "outputs/xhs_login")) / get_account_id()
    ).resolve()
    file_path = (output_dir / filename).resolve()

    if output_dir != file_path.parent or not file_path.is_file():
        raise HTTPException(status_code=404, detail="二维码文件不存在")

    return FileResponse(file_path, media_type="image/png")


@router.get("/xhs/login-qrcode/preview", response_class=HTMLResponse)
async def preview_xhs_login_qrcode(request: Request):
    """HTML 预览页：内嵌 QR 码图片 + 过期倒计时 + 扫码提示。"""
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    meta = xiaohongshu_publisher._load_cached_login_qrcode(account_id=get_account_id())

    if not meta or not meta.get("qr_filename"):
        return HTMLResponse(
            "<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
            "<h2>暂无可用的登录二维码</h2>"
            "<p>请先调用 <code>get_xhs_login_qrcode</code> 生成二维码</p>"
            "</body></html>",
            status_code=404,
        )

    qr_filename = meta["qr_filename"]
    _, qr_url = _build_xhs_qrcode_urls(request, qr_filename)
    expires_at = meta.get("expires_at", "")
    message = meta.get("message", "请使用小红书 App 扫码登录")

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>小红书登录二维码</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif;
         display: flex; flex-direction: column; align-items: center;
         justify-content: center; min-height: 100vh; margin: 0;
         background: #f5f5f5; color: #333; }}
  .card {{ background: #fff; border-radius: 16px; padding: 40px;
           box-shadow: 0 4px 24px rgba(0,0,0,.08); text-align: center;
           max-width: 420px; width: 90%; }}
  img {{ max-width: 280px; border-radius: 8px; margin: 20px 0; }}
  .msg {{ font-size: 16px; margin-bottom: 12px; }}
  .timer {{ font-size: 14px; color: #888; margin-top: 8px; }}
  .expired {{ color: #e53935; font-weight: bold; }}
  .hint {{ font-size: 13px; color: #999; margin-top: 16px; }}
</style>
</head>
<body>
<div class="card">
  <h2>🔐 小红书扫码登录</h2>
  <p class="msg">{message}</p>
  <img src="{qr_url}" alt="登录二维码" />
  <div class="timer" id="timer"></div>
  <p class="hint">扫码后关闭此页面，回到 CLI 确认登录状态</p>
</div>
<script>
(function() {{
  var exp = "{expires_at}";
  if (!exp) return;
  var timer = document.getElementById("timer");
  function tick() {{
    var now = Date.now(), end = new Date(exp).getTime();
    var left = Math.max(0, Math.floor((end - now) / 1000));
    if (left <= 0) {{ timer.className = "timer expired"; timer.textContent = "⚠️ 二维码已过期，请重新获取"; return; }}
    var m = Math.floor(left / 60), s = left % 60;
    timer.textContent = "⏱ 剩余 " + m + ":" + (s < 10 ? "0" : "") + s;
    setTimeout(tick, 1000);
  }}
  tick();
}})();
</script>
</body>
</html>"""
    return HTMLResponse(html)


@router.post("/xhs/login/reset")
async def reset_xhs_login(account_id: Optional[str] = None):
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    return await xiaohongshu_publisher.reset_login(account_id=account_id)


@router.post("/xhs/submit-verification")
async def submit_xhs_verification(request: Request):
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher
    from app.schemas import XhsVerificationRequest, XhsVerificationResponse

    body = await request.json()
    req = XhsVerificationRequest(**body)
    result = await xiaohongshu_publisher.submit_verification(
        req.session_id,
        req.code,
        account_id=body.get("account_id"),
    )
    return XhsVerificationResponse(**result)


@router.get("/xhs/check-login-session/{session_id}")
async def check_xhs_login_session(session_id: str, account_id: Optional[str] = None):
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    return await xiaohongshu_publisher.check_login_session(
        session_id, account_id=account_id
    )


async def publish_to_xhs(request: XhsPublishRequest, http_request: Request):
    """手动发布内容到小红书"""
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher
    from app.schemas import XhsPublishRequest, XhsPublishResponse

    if not request.title or not request.content:
        return XhsPublishResponse(success=False, message="标题和内容不能为空")

    if not request.images:
        return XhsPublishResponse(success=False, message="至少需要一张图片")

    result = await xiaohongshu_publisher.publish_content(
        title=request.title,
        content=request.content,
        images=request.images,
        tags=request.tags,
        account_id=getattr(request, "account_id", None),
    )
    result = _enrich_xhs_publish_result(http_request, result)

    return XhsPublishResponse(
        success=result.get("success", False),
        message=result.get("message") or result.get("error", "发布失败"),
        login_required=result.get("login_required", False),
        login_qrcode=result.get("login_qrcode"),
        qr_image_url=result.get("qr_image_url"),
        qr_image_route=result.get("qr_image_route"),
        qr_image_path=result.get("qr_image_path"),
        expires_at=result.get("expires_at"),
        data=result.get("data"),
    )


# ---- Phase 1: Cookie 注入 ----


@router.post("/xhs/upload-cookies", response_model=XhsUploadCookiesResponse)
async def upload_xhs_cookies(request: XhsUploadCookiesRequest):
    """上传 cookies 到 xhs-mcp sidecar 的挂载路径并验证登录态。"""
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    result = await xiaohongshu_publisher.verify_and_save_cookies(request.cookies)
    return XhsUploadCookiesResponse(**result)


# ---- Phase 2: Playwright 登录代理 ----


@router.get("/xhs/login-qrcode-v2", response_model=XhsLoginQrcodeResponse)
async def get_xhs_login_qrcode_v2(request: Request):
    """通过 Playwright 代理（renderer 服务）获取小红书登录二维码。"""
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    result = await xiaohongshu_publisher.start_playwright_login()
    if not result.get("success"):
        return XhsLoginQrcodeResponse(
            success=False,
            message=result.get("message", "Playwright 登录启动失败"),
            login_method="playwright",
        )

    qr_filename = result.get("qr_filename", "")
    qr_route, qr_url = ("", "")
    if qr_filename:
        qr_route, qr_url = _build_xhs_qrcode_urls(request, qr_filename)

    return XhsLoginQrcodeResponse(
        success=True,
        message=result.get("message", "请使用小红书 App 扫码登录"),
        qr_image_url=qr_url or None,
        qr_image_route=qr_route or None,
        qr_image_path=result.get("qr_image_path"),
        expires_at=result.get("expires_at"),
        login_method="playwright",
        session_id=result.get("session_id"),
    )


@router.get("/xhs/login-qrcode-v2/status/{session_id}")
async def poll_xhs_login_v2(session_id: str):
    """轮询 Playwright 登录状态。"""
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher

    return await xiaohongshu_publisher.poll_playwright_login(session_id)


# ============================================================
# Card Render API (proxy to renderer service)
# ============================================================
from app.services.card_render_client import card_render_client


@router.get("/card-previews/{filename}", name="get_card_preview_file")
async def get_card_preview_file(filename: str):
    """返回卡片预览图片文件。"""
    output_dir = _get_card_preview_output_dir()
    file_path = (output_dir / filename).resolve()

    if output_dir != file_path.parent or not file_path.is_file():
        raise HTTPException(status_code=404, detail="卡片预览文件不存在")

    return FileResponse(file_path, media_type="image/png", filename=filename)


@router.post("/cards/title", response_model=CardRenderResponse)
async def render_title_card(request: TitleCardRenderRequest, http_request: Request):
    """渲染标题卡"""
    result = await card_render_client.render_title(
        title=request.title,
        emoji=request.emoji,
        theme=request.theme,
        emoji_position=request.emoji_position,
    )
    result = _enrich_card_render_result(http_request, result)
    return CardRenderResponse(**result)


@router.post("/cards/impact", response_model=CardRenderResponse)
async def render_impact_card(request: ImpactCardRenderRequest, http_request: Request):
    """渲染影响判断卡"""
    result = await card_render_client.render_impact(
        title=request.title,
        summary=request.summary,
        insight=request.insight,
        signals=request.signals,
        actions=request.actions,
        confidence=request.confidence,
        tags=request.tags,
    )
    result = _enrich_card_render_result(http_request, result)
    return CardRenderResponse(**result)


@router.post("/cards/radar", response_model=CardRenderResponse)
async def render_radar_card(request: RadarCardRenderRequest, http_request: Request):
    """渲染雷达图卡"""
    result = await card_render_client.render_radar(
        labels=request.labels,
        datasets=[
            d if isinstance(d, dict) else d.model_dump() for d in request.datasets
        ],
    )
    result = _enrich_card_render_result(http_request, result)
    return CardRenderResponse(**result)


@router.post("/cards/timeline", response_model=CardRenderResponse)
async def render_timeline_card(
    request: TimelineCardRenderRequest, http_request: Request
):
    """渲染辩论时间线卡"""
    result = await card_render_client.render_timeline(timeline=request.timeline)
    result = _enrich_card_render_result(http_request, result)
    return CardRenderResponse(**result)


@router.post("/cards/trend", response_model=CardRenderResponse)
async def render_trend_card(request: TrendCardRenderRequest, http_request: Request):
    """渲染趋势图卡"""
    result = await card_render_client.render_trend(
        stage=request.stage,
        growth=request.growth,
        curve=request.curve,
    )
    result = _enrich_card_render_result(http_request, result)
    return CardRenderResponse(**result)


@router.post("/cards/daily-rank", response_model=CardRenderResponse)
async def render_daily_rank_card(
    request: DailyRankCardRenderRequest, http_request: Request
):
    """渲染每日榜单卡"""
    result = await card_render_client.render_daily_rank(
        date=request.date,
        topics=[t if isinstance(t, dict) else t.model_dump() for t in request.topics],
        title=request.title,
    )
    result = _enrich_card_render_result(http_request, result)
    return CardRenderResponse(**result)


@router.post("/cards/hot-topic", response_model=CardRenderResponse)
async def render_hot_topic_card(
    request: HotTopicCardRenderRequest, http_request: Request
):
    """渲染热点详情卡"""
    result = await card_render_client.render_hot_topic(
        title=request.title,
        summary=request.summary,
        tags=request.tags,
        source_count=request.source_count,
        score=request.score,
        date=request.date,
        sources=request.sources,
    )
    result = _enrich_card_render_result(http_request, result)
    return CardRenderResponse(**result)
