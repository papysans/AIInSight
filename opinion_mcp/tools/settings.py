"""
MCP 设置工具

包含配置和 Webhook 相关的 MCP 工具:
- get_settings: 获取当前分析配置
- register_webhook: 注册进度推送 Webhook
"""

from typing import Any, Dict, List, Optional
from loguru import logger

from opinion_mcp.config import config
from opinion_mcp.services.account_context import get_account_id
from opinion_mcp.services.job_manager import job_manager
from opinion_mcp.services.webhook_manager import webhook_manager


# ============================================================
# 6.6 get_settings 工具 - 获取配置 (含 emoji)
# ============================================================


async def get_settings() -> Dict[str, Any]:
    """
    获取当前的分析配置，包括默认来源组、图片数量等

    Returns:
        Dict 包含:
        - success: bool - 是否成功
        - default_source_groups: List[str] - 默认来源组
        - image_count: int - 默认图片数量
        - debate_rounds: int - 默认辩论轮数
        - available_sources: List[Dict] - 可用来源列表，每个包含:
            - code: str - 来源代码
            - name: str - 来源名称
            - emoji: str - 来源 emoji 图标
    """
    logger.debug("[get_settings] 获取配置")

    try:
        # 构建可用来源列表（包含 emoji）
        available_sources = []
        for source in config.AVAILABLE_SOURCES:
            available_sources.append(
                {
                    "code": source["code"],
                    "name": source["name"],
                    "emoji": source["emoji"],
                }
            )

        return {
            "success": True,
            "default_source_groups": config.DEFAULT_SOURCE_GROUPS,
            "source_groups": config.SOURCE_GROUPS,
            "depth_presets": list(config.DEPTH_PRESETS.keys()),
            "image_count": config.DEFAULT_IMAGE_COUNT,
            "debate_rounds": config.DEFAULT_DEBATE_ROUNDS,
            "available_sources": available_sources,
        }

    except Exception as e:
        logger.exception(f"[get_settings] 获取配置异常: {e}")
        return {
            "success": False,
            "error": str(e),
            "default_source_groups": [],
            "source_groups": {},
            "depth_presets": [],
            "image_count": 0,
            "debate_rounds": 2,
            "available_sources": [],
        }


# ============================================================
# 6.7 register_webhook 工具 - 注册进度推送
# ============================================================


async def register_webhook(
    callback_url: str,
    job_id: str,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    注册进度推送的 Webhook URL

    MCP Server 会在关键节点主动推送进度到指定 URL。

    推送时机:
    - 任务开始
    - 每个来源检索完成
    - 进入新的分析步骤
    - 辩论轮次更新
    - 图片生成进度
    - 任务完成或失败

    Args:
        callback_url: 接收进度推送的 URL
        job_id: 要监听的任务 ID

    Returns:
        Dict 包含:
        - success: bool - 是否成功
        - message: str - 消息
    """
    logger.info(f"[register_webhook] 注册 Webhook: job_id={job_id}, url={callback_url}")

    account_id = account_id or get_account_id()

    # 参数验证
    if not callback_url:
        return {
            "success": False,
            "message": "callback_url 不能为空",
        }

    if not job_id:
        return {
            "success": False,
            "message": "job_id 不能为空",
        }

    # 验证 URL 格式
    if not callback_url.startswith(("http://", "https://")):
        return {
            "success": False,
            "message": "callback_url 必须是有效的 HTTP/HTTPS URL",
        }

    # 检查任务是否存在
    job = job_manager.get_job(job_id, account_id=account_id)
    if not job:
        return {
            "success": False,
            "message": f"任务不存在: {job_id}",
        }

    # 检查任务是否已完成
    if job.is_completed or job.is_failed:
        return {
            "success": False,
            "message": "任务已结束，无法注册 Webhook",
        }

    try:
        # 注册 Webhook
        success = webhook_manager.register(job_id, callback_url, account_id=account_id)

        if not success:
            return {
                "success": False,
                "message": "Webhook 注册失败",
            }

        # 同时更新任务的 webhook_url
        job_manager.set_webhook_url(job_id, callback_url, account_id=account_id)

        logger.info(f"[register_webhook] 注册成功: job_id={job_id}")

        return {
            "success": True,
            "message": "Webhook 注册成功",
        }

    except Exception as e:
        logger.exception(f"[register_webhook] 注册异常: {e}")
        return {
            "success": False,
            "message": f"注册异常: {str(e)}",
        }


# ============================================================
# 导出工具函数
# ============================================================

__all__ = [
    "get_settings",
    "register_webhook",
]
