"""
MCP AI Daily 工具

包含 AI 日报相关的 MCP 工具:
- get_ai_daily: 获取今日 AI 日报
- analyze_ai_topic: 对 AI 日报话题运行深度分析
- generate_ai_daily_cards: 为 AI 日报话题生成卡片套图
"""

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from opinion_mcp.config import config


def _summarize_cards(cards: Dict[str, Any]) -> Dict[str, Any]:
    """Strip large inline base64 payloads from MCP responses while keeping preview paths."""
    summarized: Dict[str, Any] = {}
    for name, card in (cards or {}).items():
        if not isinstance(card, dict):
            summarized[name] = card
            continue
        item = dict(card)
        if item.pop("image_data_url", None):
            item["preview_available"] = True
        summarized[name] = item
    return summarized


async def get_ai_daily(
    force_refresh: bool = False,
    sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    获取今日 AI 日报（多源采集 → 评分 → 聚合）

    Args:
        force_refresh: 是否强制刷新（忽略缓存）
        sources: 指定数据源列表，留空使用全部启用源

    Returns:
        Dict 包含:
        - success: bool
        - date: str - 日期
        - topics: List[Dict] - 聚合话题列表
        - total: int - 话题数
        - sources_used: List[str] - 使用的数据源
    """
    logger.info(f"[get_ai_daily] force_refresh={force_refresh}, sources={sources}")

    try:
        payload: Dict[str, Any] = {"force_refresh": force_refresh}
        if sources:
            payload["sources"] = sources

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{config.BACKEND_URL.rstrip('/')}/api/ai-daily/collect",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        topics = data.get("topics", [])
        return {
            "success": True,
            "date": data.get("date", ""),
            "topics": [
                {
                    "topic_id": t.get("topic_id"),
                    "title": t.get("title"),
                    "summary_zh": t.get("summary_zh", ""),
                    "tags": t.get("tags", []),
                    "source_count": len(t.get("sources", [])),
                    "scores": t.get("scores", {}),
                }
                for t in topics
            ],
            "total": data.get("total", len(topics)),
            "sources_used": data.get("sources_used", []),
            "collected_at": data.get("collected_at", ""),
        }

    except Exception as e:
        logger.error(f"[get_ai_daily] 失败: {e}")
        return {
            "success": False,
            "error": f"获取 AI 日报失败: {str(e)}",
            "topics": [],
            "total": 0,
        }


async def analyze_ai_topic(
    topic_id: str,
    depth: str = "standard",
) -> Dict[str, Any]:
    """
    对 AI 日报中的某个话题启动深度分析（走统一 evidence-first 工作流）

    Args:
        topic_id: 话题 ID（从 get_ai_daily 返回）
        depth: 分析深度 quick / standard / deep

    Returns:
        Dict 包含 job_id 和分析结果
    """
    logger.info(f"[analyze_ai_topic] topic_id={topic_id}, depth={depth}")

    if depth not in ("quick", "standard", "deep"):
        depth = "standard"

    try:
        # Step 1: 获取话题详情
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{config.BACKEND_URL.rstrip('/')}/api/ai-daily/{topic_id}",
            )
            resp.raise_for_status()
            topic_data = resp.json().get("topic", {})

        topic_title = topic_data.get("title", "")
        if not topic_title:
            return {"success": False, "error": f"话题 {topic_id} 无标题", "topic_id": topic_id}

        # 构建含上下文的 topic 文本
        topic_text = topic_title
        summary_zh = topic_data.get("summary_zh", "")
        if summary_zh:
            topic_text += f"\n{summary_zh}"

        # Step 2: 走统一 analyze_topic 工作流
        from opinion_mcp.tools.analyze import analyze_topic
        result = await analyze_topic(
            topic=topic_text,
            depth=depth,
        )

        if result.get("success"):
            result["topic_id"] = topic_id

        return result

    except Exception as e:
        logger.error(f"[analyze_ai_topic] 失败: {e}")
        return {
            "success": False,
            "error": f"分析 AI 话题失败: {str(e)}",
            "topic_id": topic_id,
        }


async def generate_ai_daily_cards(
    topic_id: str,
    card_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    为 AI 日报话题生成卡片套图

    Args:
        topic_id: 话题 ID
        card_types: 要生成的卡片类型列表，可选 title / hot-topic / daily-rank

    Returns:
        Dict 包含各卡片的 dataURL
    """
    logger.info(f"[generate_ai_daily_cards] topic_id={topic_id}, card_types={card_types}")

    try:
        payload: Dict[str, Any] = {}
        if card_types:
            payload["card_types"] = card_types

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{config.BACKEND_URL.rstrip('/')}/api/ai-daily/{topic_id}/cards",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "success": True,
            "topic_id": topic_id,
            "cards": _summarize_cards(data.get("cards", {})),
        }

    except Exception as e:
        logger.error(f"[generate_ai_daily_cards] 失败: {e}")
        return {
            "success": False,
            "error": f"生成卡片失败: {str(e)}",
            "topic_id": topic_id,
        }


async def publish_ai_daily(
    topic_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    card_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    将 AI 日报话题发布到小红书

    Args:
        topic_id: 话题 ID（从 get_ai_daily 返回）
        title: 自定义标题，留空使用话题标题
        content: 自定义正文，留空使用话题摘要
        tags: 自定义标签列表
        card_types: 卡片类型列表 (title/hot-topic/daily-rank)，留空使用默认

    Returns:
        Dict 包含发布结果
    """
    logger.info(f"[publish_ai_daily] topic_id={topic_id}")

    try:
        payload: Dict[str, Any] = {}
        if title:
            payload["title"] = title
        if content:
            payload["content"] = content
        if tags:
            payload["tags"] = tags
        if card_types:
            payload["card_types"] = card_types

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{config.BACKEND_URL.rstrip('/')}/api/ai-daily/{topic_id}/publish",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "success": data.get("success", True),
            "topic_id": topic_id,
            "message": data.get("message") or data.get("error"),
            "result": data,
            "login_required": data.get("login_required", False),
            "login_qrcode": data.get("login_qrcode"),
            "qr_image_url": data.get("qr_image_url"),
            "qr_image_route": data.get("qr_image_route"),
            "qr_image_path": data.get("qr_image_path"),
            "expires_at": data.get("expires_at"),
        }

    except Exception as e:
        logger.error(f"[publish_ai_daily] 失败: {e}")
        return {
            "success": False,
            "error": f"发布 AI 日报失败: {str(e)}",
            "topic_id": topic_id,
        }


async def generate_ai_daily_ranking_cards(
    limit: int = 10,
    title: Optional[str] = None,
    card_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """为今日 AI 热点整榜生成卡片套图。"""
    logger.info(f"[generate_ai_daily_ranking_cards] limit={limit}, card_types={card_types}")

    try:
        payload: Dict[str, Any] = {"limit": limit}
        if title:
            payload["title"] = title
        if card_types:
            payload["card_types"] = card_types

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{config.BACKEND_URL.rstrip('/')}/api/ai-daily/ranking/cards",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "success": True,
            "date": data.get("date", ""),
            "limit": data.get("limit", limit),
            "title": data.get("title", ""),
            "cards": _summarize_cards(data.get("cards", {})),
        }

    except Exception as e:
        logger.error(f"[generate_ai_daily_ranking_cards] 失败: {e}")
        return {
            "success": False,
            "error": f"生成 AI 榜单卡片失败: {str(e)}",
        }


async def publish_ai_daily_ranking(
    limit: int = 10,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    card_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """将今日 AI 热点整榜发布到小红书。"""
    logger.info(f"[publish_ai_daily_ranking] limit={limit}")

    try:
        payload: Dict[str, Any] = {"limit": limit}
        if title:
            payload["title"] = title
        if content:
            payload["content"] = content
        if tags:
            payload["tags"] = tags
        if card_types:
            payload["card_types"] = card_types

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{config.BACKEND_URL.rstrip('/')}/api/ai-daily/ranking/publish",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "success": data.get("success", True),
            "date": data.get("date", ""),
            "limit": data.get("limit", limit),
            "title": data.get("title", ""),
            "message": data.get("message") or data.get("error"),
            "result": data,
            "login_required": data.get("login_required", False),
            "login_qrcode": data.get("login_qrcode"),
            "qr_image_url": data.get("qr_image_url"),
            "qr_image_route": data.get("qr_image_route"),
            "qr_image_path": data.get("qr_image_path"),
            "expires_at": data.get("expires_at"),
        }

    except Exception as e:
        logger.error(f"[publish_ai_daily_ranking] 失败: {e}")
        return {
            "success": False,
            "error": f"发布 AI 榜单失败: {str(e)}",
        }
