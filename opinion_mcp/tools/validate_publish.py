"""
MCP 发布验证工具

提供发布前的验证功能:
- validate_publish: 验证发布条件是否满足

Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import httpx
from loguru import logger

from opinion_mcp.config import config
from opinion_mcp.services.account_context import get_account_id
from opinion_mcp.services.job_manager import job_manager
from opinion_mcp.utils.url_validator import validate_urls, URLValidationResult


# XHS-MCP 服务配置
XHS_MCP_TIMEOUT = 5.0  # 秒


@dataclass
class ImageValidationDetail:
    """单个图片的验证详情"""

    url: str
    valid: bool
    status_code: Optional[int] = None
    error: Optional[str] = None


@dataclass
class ValidatePublishResult:
    """
    发布验证结果

    Property 5: Validation Result Completeness
    For any call to `validate_publish`, the result SHALL contain:
    - xhs_service_ok (boolean)
    - images_valid (count)
    - images_invalid (count)
    - image_details (list with status for each image)
    - can_publish (boolean)
    """

    xhs_service_ok: bool
    images_valid: int
    images_invalid: int
    image_details: List[Dict[str, Any]]
    can_publish: bool
    suggestions: List[str]
    job_id: Optional[str] = None
    error: Optional[str] = None


async def check_xhs_service() -> tuple[bool, Optional[str]]:
    """
    检查 XHS-MCP 服务是否可用

    Returns:
        Tuple[bool, Optional[str]]: (是否可用, 错误信息)
    """
    xhs_mcp_url = config.XHS_MCP_URL
    try:
        async with httpx.AsyncClient(timeout=XHS_MCP_TIMEOUT) as client:
            response = await client.get(xhs_mcp_url)

            # Some MCP servers only accept POST on `/mcp`; 405 still proves the
            # endpoint is reachable and the service is alive.
            if response.status_code in (200, 405):
                return True, None
            else:
                return False, f"XHS-MCP 服务返回状态码 {response.status_code}"

    except httpx.ConnectError:
        return False, f"无法连接到 XHS-MCP 服务 ({xhs_mcp_url})"
    except httpx.TimeoutException:
        return False, "XHS-MCP 服务响应超时"
    except Exception as e:
        return False, f"检查 XHS-MCP 服务时出错: {str(e)}"


def convert_validation_results(
    results: List[URLValidationResult],
) -> List[Dict[str, Any]]:
    """将 URLValidationResult 转换为字典列表"""
    return [
        {
            "url": r.url,
            "valid": r.valid,
            "status_code": r.status_code,
            "error": r.error,
        }
        for r in results
    ]


async def validate_publish(
    job_id: Optional[str] = None,
    account_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    验证发布条件是否满足

    检查内容:
    1. XHS-MCP 服务是否可用
    2. 任务是否存在且已完成
    3. 图片 URL 是否有效

    Args:
        job_id: 任务 ID，留空则使用最近完成的任务

    Returns:
        Dict 包含验证结果:
        - xhs_service_ok: bool - XHS-MCP 服务是否可用
        - images_valid: int - 有效图片数量
        - images_invalid: int - 无效图片数量
        - image_details: List[Dict] - 每个图片的验证详情
        - can_publish: bool - 是否可以发布
        - suggestions: List[str] - 修复建议
        - job_id: str - 任务 ID
        - error: str - 错误信息（如果有）
    """
    logger.info(f"[validate_publish] 开始验证: job_id={job_id}")
    account_id = account_id or get_account_id()

    suggestions: List[str] = []

    # 1. 检查 XHS-MCP 服务
    xhs_ok, xhs_error = await check_xhs_service()
    if not xhs_ok:
        suggestions.append(f"启动 XHS-MCP 服务: {xhs_error}")
        logger.warning(f"[validate_publish] XHS-MCP 服务不可用: {xhs_error}")

    # 2. 获取任务
    if job_id:
        job = job_manager.get_job(job_id, account_id=account_id)
    else:
        job = job_manager.get_latest_completed_job(account_id=account_id)
        if job:
            job_id = job.job_id

    if not job:
        error_msg = "任务不存在" if job_id else "没有已完成的任务"
        return asdict(
            ValidatePublishResult(
                xhs_service_ok=xhs_ok,
                images_valid=0,
                images_invalid=0,
                image_details=[],
                can_publish=False,
                suggestions=suggestions + [error_msg],
                job_id=job_id,
                error=error_msg,
            )
        )

    # 3. 检查任务状态
    if job.is_running:
        return asdict(
            ValidatePublishResult(
                xhs_service_ok=xhs_ok,
                images_valid=0,
                images_invalid=0,
                image_details=[],
                can_publish=False,
                suggestions=suggestions + ["等待任务完成"],
                job_id=job_id,
                error="任务仍在运行中",
            )
        )

    if job.is_failed:
        return asdict(
            ValidatePublishResult(
                xhs_service_ok=xhs_ok,
                images_valid=0,
                images_invalid=0,
                image_details=[],
                can_publish=False,
                suggestions=suggestions + ["重新运行分析任务"],
                job_id=job_id,
                error=f"任务失败: {job.error_message}",
            )
        )

    # 4. 收集所有图片 URL
    result = job.result
    if not result:
        return asdict(
            ValidatePublishResult(
                xhs_service_ok=xhs_ok,
                images_valid=0,
                images_invalid=0,
                image_details=[],
                can_publish=False,
                suggestions=suggestions + ["任务没有结果数据"],
                job_id=job_id,
                error="任务没有结果数据",
            )
        )

    image_urls: List[str] = []

    # 收集数据卡片图片
    if result.cards:
        cards = result.cards
        if cards.title_card:
            image_urls.append(cards.title_card)
        impact_card = getattr(cards, "impact_card", None)
        if impact_card:
            image_urls.append(impact_card)
        if cards.debate_timeline:
            image_urls.append(cards.debate_timeline)
        if cards.trend_analysis:
            image_urls.append(cards.trend_analysis)
        if cards.platform_radar:
            image_urls.append(cards.platform_radar)

    # 收集 AI 生成图片
    if result.ai_images:
        image_urls.extend(result.ai_images)

    if not image_urls:
        return asdict(
            ValidatePublishResult(
                xhs_service_ok=xhs_ok,
                images_valid=0,
                images_invalid=0,
                image_details=[],
                can_publish=False,
                suggestions=suggestions + ["没有可发布的图片，请先生成 AI 配图"],
                job_id=job_id,
                error="没有图片",
            )
        )

    # 5. 验证所有图片 URL
    logger.info(f"[validate_publish] 验证 {len(image_urls)} 个图片 URL")
    validation_results = await validate_urls(image_urls, timeout=10.0, concurrency=5)

    # 统计结果
    valid_count = sum(1 for r in validation_results if r.valid)
    invalid_count = len(validation_results) - valid_count

    # 转换为字典格式
    image_details = convert_validation_results(validation_results)

    # 添加无效图片的建议
    if invalid_count > 0:
        invalid_urls = [r.url for r in validation_results if not r.valid]
        suggestions.append(f"{invalid_count} 个图片 URL 无效，可能需要重新生成")
        for r in validation_results:
            if not r.valid:
                logger.warning(f"[validate_publish] 无效图片: {r.url} - {r.error}")

    # 6. 判断是否可以发布
    can_publish = xhs_ok and valid_count > 0

    if not can_publish and valid_count == 0:
        suggestions.append("所有图片都无效，请重新生成图片")

    logger.info(
        f"[validate_publish] 验证完成: xhs_ok={xhs_ok}, valid={valid_count}, invalid={invalid_count}, can_publish={can_publish}"
    )

    return asdict(
        ValidatePublishResult(
            xhs_service_ok=xhs_ok,
            images_valid=valid_count,
            images_invalid=invalid_count,
            image_details=image_details,
            can_publish=can_publish,
            suggestions=suggestions,
            job_id=job_id,
            error=None,
        )
    )


# ============================================================
# 导出工具函数
# ============================================================

__all__ = [
    "validate_publish",
    "ValidatePublishResult",
]
