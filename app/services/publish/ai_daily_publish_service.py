"""
AI Daily 发布服务

将 AI 日报话题的分析结果和卡片发布到小红书。
复用现有 XiaohongshuPublisher 的 MCP 调用能力。
"""

from typing import Dict, Any, List, Optional
from loguru import logger

from app.services.xiaohongshu_publisher import xiaohongshu_publisher
from app.services.card_render_client import card_render_client
from app.services.ai_daily_pipeline import get_topic_by_id, collect_ai_daily


async def publish_ai_daily_topic(
    topic_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    card_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    发布 AI 日报话题到小红书。

    1. 查找话题
    2. 生成所需卡片（title + hot-topic by default）
    3. 调用 XHS MCP 发布

    Args:
        topic_id: 话题 ID
        title: 自定义标题（留空用话题标题）
        content: 自定义正文（留空用话题摘要）
        tags: 自定义标签
        card_types: 要生成的卡片类型
    """
    topic = await get_topic_by_id(topic_id)
    if not topic:
        return {"success": False, "error": f"Topic {topic_id} not found"}

    pub_title = title or topic.title
    pub_content = content or topic.summary_zh or topic.title
    pub_tags = tags or topic.tags or []

    # Generate cards
    types = card_types or ["title", "hot-topic"]
    images: List[str] = []

    for ct in types:
        try:
            if ct == "title":
                result = await card_render_client.render_title(title=pub_title)
            elif ct == "hot-topic":
                result = await card_render_client.render_hot_topic(
                    title=pub_title,
                    summary=pub_content,
                    tags=pub_tags,
                    source_count=topic.source_count or len(topic.sources or []),
                    score=topic.final_score,
                    sources=[s.source for s in (topic.sources or [])[:4] if getattr(s, "source", None)],
                )
            elif ct == "daily-rank":
                from datetime import date as date_cls
                result = await card_render_client.render_daily_rank(
                    date=date_cls.today().isoformat(),
                    topics=[{
                        "rank": 1,
                        "title": topic.title,
                        "score": topic.final_score,
                        "tags": (topic.tags or [])[:3],
                    }],
                )
            else:
                continue

            if result.get("success") and result.get("image_data_url"):
                images.append(result["image_data_url"])
        except Exception as e:
            logger.warning(f"[AiDailyPublish] Failed to render {ct}: {e}")

    if not images:
        return {"success": False, "error": "未能生成任何卡片图片"}

    # Publish via XHS MCP
    result = await xiaohongshu_publisher.publish_content(
        title=pub_title,
        content=pub_content,
        images=images,
        tags=pub_tags,
    )

    return result


def _topic_to_rank_item(topic, rank: int) -> Dict[str, Any]:
    return {
        "rank": rank,
        "title": topic.title,
        "score": topic.final_score,
        "tags": (topic.tags or [])[:3],
    }


def _default_ranking_title(date_text: str, limit: int) -> str:
    return f"{date_text} AI 热点榜单 Top {limit}"


def _default_ranking_content(date_text: str, topics: List[Any]) -> str:
    lines = [f"{date_text} AI 热点榜单速递", ""]
    for idx, topic in enumerate(topics[:5], 1):
        lines.append(f"{idx}. {topic.title}")
        summary = (topic.summary_zh or "").strip()
        if summary:
            if len(summary) > 42:
                summary = f"{summary[:42]}…"
            lines.append(f"   {summary}")
        lines.append("")
    lines.append("#AI热点 #AI日报 #科技趋势")
    return "\n".join(lines).strip()


def _default_ranking_tags(topics: List[Any], custom_tags: Optional[List[str]] = None) -> List[str]:
    tags: List[str] = []
    for tag in (custom_tags or []):
        if tag not in tags:
            tags.append(tag)
    for topic in topics[:5]:
        for tag in (topic.tags or [])[:2]:
            if tag not in tags:
                tags.append(tag)
    for tag in ["AI热点", "AI日报", "科技趋势"]:
        if tag not in tags:
            tags.append(tag)
    return tags[:8]


async def generate_ai_daily_ranking_cards(
    limit: int = 10,
    title: Optional[str] = None,
    card_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """生成今日 AI 热点整榜卡片。"""
    ranking = await collect_ai_daily(force_refresh=False)
    topics = (ranking.topics or [])[: max(1, min(limit, 10))]
    if not topics:
        return {"success": False, "error": "今日榜单为空，无法生成卡片"}

    title_text = title or _default_ranking_title(ranking.date, len(topics))
    types = card_types or ["title", "daily-rank"]
    cards: Dict[str, Any] = {}

    for ct in types:
        if ct == "title":
            result = await card_render_client.render_title(title=title_text, emoji="📊", theme="sunset")
            cards["title"] = result
        elif ct == "daily-rank":
            result = await card_render_client.render_daily_rank(
                date=ranking.date,
                title="AI 每日热点榜单",
                topics=[_topic_to_rank_item(topic, idx) for idx, topic in enumerate(topics, 1)],
            )
            cards["daily-rank"] = result

    return {
        "success": True,
        "date": ranking.date,
        "total": ranking.total,
        "limit": len(topics),
        "title": title_text,
        "cards": cards,
    }


async def publish_ai_daily_ranking(
    limit: int = 10,
    title: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    card_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """将今日 AI 热点整榜发布到小红书。"""
    ranking = await collect_ai_daily(force_refresh=False)
    topics = (ranking.topics or [])[: max(1, min(limit, 10))]
    if not topics:
        return {"success": False, "error": "今日榜单为空，无法发布"}

    title_text = title or _default_ranking_title(ranking.date, len(topics))
    content_text = content or _default_ranking_content(ranking.date, topics)
    final_tags = _default_ranking_tags(topics, tags)

    card_result = await generate_ai_daily_ranking_cards(
        limit=len(topics),
        title=title_text,
        card_types=card_types or ["title", "daily-rank"],
    )
    if not card_result.get("success"):
        return card_result

    images: List[str] = []
    for result in (card_result.get("cards") or {}).values():
        if result.get("success") and result.get("image_data_url"):
            images.append(result["image_data_url"])

    if not images:
        return {"success": False, "error": "未能生成整榜卡片图片"}

    publish_result = await xiaohongshu_publisher.publish_content(
        title=title_text,
        content=content_text,
        images=images,
        tags=final_tags,
    )

    if publish_result.get("success"):
        publish_result.update({
            "date": ranking.date,
            "limit": len(topics),
            "title": title_text,
        })
    return publish_result
