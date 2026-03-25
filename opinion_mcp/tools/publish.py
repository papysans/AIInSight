"""
MCP 发布工具

包含小红书发布相关的 MCP 工具。
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from opinion_mcp.services.account_context import get_account_id
from opinion_mcp.services.backend_client import backend_client


# ============================================================
# 敏感关键词预检（Section 7.2 preflight）
# ============================================================

_BLOCKED_KEYWORDS = [
    "习近平", "政治局", "中央委员会", "台湾独立", "天安门", "法轮功",
    "新疆集中营", "西藏独立", "香港独立", "颠覆国家政权",
]


def _preflight_content_check(title: str, content: str) -> Optional[Dict[str, Any]]:
    """扫描 title + content 中的敏感关键词。命中则返回拒绝响应，否则返回 None。"""
    combined = (title or "") + " " + (content or "")
    for kw in _BLOCKED_KEYWORDS:
        if kw in combined:
            return {
                "success": False,
                "error": "content_policy_violation",
                "reason": "内容安全策略阻止发布",
            }
    return None


# ============================================================
# publish_xhs_note - 核心发布工具
# ============================================================


async def publish_xhs_note(
    title: str,
    content: str,
    images: List[str],
    tags: Optional[List[str]] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """发布小红书笔记（接受原始内容）

    Args:
        title: 笔记标题
        content: 笔记正文
        images: 图片路径或 URL 列表
        tags: 话题标签列表（可选）
        account_id: 账号 ID（可选，从上下文自动获取）

    Returns:
        { "success": bool, "note_url": str }
    """
    logger.info(f"[publish_xhs_note] 发布到小红书: title={title[:30] if title else ''}...")
    account_id = account_id or get_account_id()

    # 参数验证
    if not title or not title.strip():
        return {"success": False, "error": "标题不能为空"}
    if not content or not content.strip():
        return {"success": False, "error": "正文不能为空"}
    if not images:
        return {"success": False, "error": "至少需要一张图片"}

    # Preflight 安全检查（Section 7.2）
    blocked = _preflight_content_check(title, content)
    if blocked:
        return blocked

    publish_tags = tags or []

    try:
        publish_result = await backend_client.publish_xhs(
            title=title,
            content=content,
            images=images,
            tags=publish_tags,
            account_id=account_id,
        )

        if not publish_result.get("success"):
            error_msg = (
                publish_result.get("message")
                or publish_result.get("error")
                or "发布失败"
            )
            logger.error(f"[publish_xhs_note] 发布失败: {error_msg}")
            failure_result: Dict[str, Any] = {
                "success": False,
                "error": error_msg,
                "note_url": None,
            }
            for extra_key in (
                "login_required",
                "login_qrcode",
                "qr_image_url",
                "qr_image_route",
                "qr_image_path",
                "expires_at",
            ):
                if extra_key in publish_result:
                    failure_result[extra_key] = publish_result.get(extra_key)
            return failure_result

        note_url = None
        data = publish_result.get("data")
        if isinstance(data, dict):
            note_url = data.get("note_url") or data.get("url")

        logger.info(f"[publish_xhs_note] 发布成功: note_url={note_url}")
        return {"success": True, "note_url": note_url}

    except Exception as e:
        logger.exception(f"[publish_xhs_note] 发布异常: {e}")
        return {"success": False, "error": str(e), "note_url": None}


# ============================================================
# XHS 登录相关工具
# ============================================================


async def check_xhs_status(account_id: Optional[str] = None) -> Dict[str, Any]:
    """检查小红书 MCP 服务可用性和登录状态。"""
    logger.info("[check_xhs_status] 检查小红书状态")
    return await backend_client.get_xhs_status(account_id=account_id)


async def get_xhs_login_qrcode(account_id: Optional[str] = None) -> Dict[str, Any]:
    """获取小红书登录二维码信息。"""
    logger.info("[get_xhs_login_qrcode] 获取登录二维码")
    result = await backend_client.get_xhs_login_qrcode(account_id=account_id)

    qr_ascii = result.get("qr_ascii")
    if qr_ascii and result.get("success"):
        result["cli_display"] = (
            f"\n{result.get('message', '请使用小红书 App 扫码登录')}\n\n"
            f"{qr_ascii}\n\n"
            f"📱 请用小红书 App 扫描上方二维码\n"
            f"⏱ 过期时间: {result.get('expires_at', '未知')}\n"
            f"🔗 浏览器预览: {result.get('qr_preview_url', 'N/A')}"
        )

    return result


async def reset_xhs_login(account_id: Optional[str] = None) -> Dict[str, Any]:
    logger.info("[reset_xhs_login] 重置登录状态")
    return await backend_client.reset_xhs_login(account_id=account_id)


async def submit_xhs_verification(
    session_id: str, code: str, account_id: Optional[str] = None
) -> Dict[str, Any]:
    logger.info(f"[submit_xhs_verification] session_id={session_id}")
    return await backend_client.submit_xhs_verification(
        session_id, code, account_id=account_id
    )


async def check_xhs_login_session(
    session_id: str, account_id: Optional[str] = None
) -> Dict[str, Any]:
    logger.info(f"[check_xhs_login_session] session_id={session_id}")
    return await backend_client.check_xhs_login_session(
        session_id, account_id=account_id
    )


async def upload_xhs_cookies(cookies_data: Any) -> Dict[str, Any]:
    """将 cookies 注入到 xhs-mcp sidecar 并验证登录态。"""
    logger.info("[upload_xhs_cookies] 注入 cookies")
    return await backend_client.upload_xhs_cookies(cookies_data)


async def get_xhs_login_qrcode_v2() -> Dict[str, Any]:
    """通过 Playwright 代理获取小红书登录二维码（不依赖 xhs-mcp 原生登录）。"""
    logger.info("[get_xhs_login_qrcode_v2] 获取 Playwright 登录二维码")
    return await backend_client.get_xhs_login_qrcode_v2()


async def poll_xhs_login_v2(session_id: str) -> Dict[str, Any]:
    """轮询 Playwright 登录状态。"""
    return await backend_client.poll_xhs_login_v2(session_id)


# ============================================================
# 导出工具函数
# ============================================================

__all__ = [
    "publish_xhs_note",
    "check_xhs_status",
    "get_xhs_login_qrcode",
    "reset_xhs_login",
    "submit_xhs_verification",
    "check_xhs_login_session",
    "upload_xhs_cookies",
    "get_xhs_login_qrcode_v2",
    "poll_xhs_login_v2",
]
