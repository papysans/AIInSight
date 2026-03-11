"""
AI Daily 发布服务

将 AI 日报话题的分析结果和卡片发布到小红书。
复用现有 XiaohongshuPublisher 的 MCP 调用能力。
"""

import re
from typing import Dict, Any, List, Optional
from loguru import logger

from app.services.xiaohongshu_publisher import xiaohongshu_publisher
from app.services.card_render_client import card_render_client
from app.services.ai_daily_pipeline import get_topic_by_id, collect_ai_daily

FALLBACK_TAGS = ["AI热点", "AI日报", "科技趋势", "人工智能", "科技资讯"]


def _contains_chinese(text: str) -> bool:
    return any("\u4e00" <= c <= "\u9fff" for c in text)


def _clean_editorial_fragment(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip())
    cleaned = cleaned.strip("，。；;:：、 ")
    if not cleaned:
        return ""
    if len(cleaned) > 28:
        cleaned = f"{cleaned[:28]}…"
    return cleaned


def _topic_signal_label(topic: Any) -> str:
    tags = [str(tag).strip().lower() for tag in (getattr(topic, "tags", None) or [])]
    sources = getattr(topic, "sources", None) or []
    source_types = {
        str(getattr(source, "source_type", "")).strip().lower() for source in sources
    }
    title = str(getattr(topic, "title", ""))

    if "research" in source_types or any(
        tag in {"论文", "research", "paper", "评测"} for tag in tags
    ):
        return "研究"
    if (
        "code" in source_types
        or any(tag in {"开源", "agent", "github"} for tag in tags)
        or "GitHub" in title
    ):
        return "开源"
    if "product" in source_types or any(
        tag in {"产品", "多模态", "tool"} for tag in tags
    ):
        return "产品"
    return "行业"


def _infer_day_themes(topics: List[Any]) -> List[str]:
    counts: Dict[str, int] = {}
    for topic in topics:
        label = _topic_signal_label(topic)
        counts[label] = counts.get(label, 0) + 1
    return [
        label
        for label, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:2]
    ]


def _topic_supporting_line(topic: Any) -> str:
    title = str(getattr(topic, "title", "")).strip()
    summary = _clean_editorial_fragment(str(getattr(topic, "summary_zh", "") or ""))
    label = _topic_signal_label(topic)
    source_count = max(1, int(getattr(topic, "source_count", 1) or 1))

    if label == "开源":
        if summary and _contains_chinese(summary) and summary != title:
            return f"像 {title} 这类开源项目今天仍然很活跃，{summary}。"
        return f"像 {title} 这类开源项目今天依旧在被讨论，开发者侧的关注还在。"
    if label == "研究":
        if summary and _contains_chinese(summary) and summary != title:
            return f"研究线也没闲着，{title} 这类话题说明 {summary}。"
        return f"研究线也没停，{title} 这类进展更像是在把能力往真实场景里压。"
    if label == "产品":
        if summary and _contains_chinese(summary) and summary != title:
            return f"产品侧最直观的是 {title}，{summary}。"
        return f"产品侧最直观的是 {title}，重点不是噱头，而是离真实可用又近了一步。"

    if summary and _contains_chinese(summary) and summary != title:
        return f"{title} 这条也值得看，{summary}。"
    if source_count >= 2:
        return f"{title} 这条被多处同时提到，至少说明它今天不算边角料。"
    return f"{title} 这条先记一笔，信号不算满，但方向已经开始露头。"


def _compose_editorial_ranking_copy(date_text: str, topics: List[Any]) -> str:
    selected = (topics or [])[:3]
    if not selected:
        return f"{date_text} 的 AI 热点不算多，但有几条方向已经开始冒头。"

    themes = _infer_day_themes(selected)
    if len(themes) >= 2:
        opening = f"今天 AI 圈比较明显的主线，是{themes[0]}和{themes[1]}这两条线在一起往前走。"
    elif themes:
        opening = f"今天 AI 圈更值得看的，不是一条孤立新闻，而是{themes[0]}方向又多了几条新动静。"
    else:
        opening = "今天 AI 圈的信息很多，但真正值得看的是几条已经能串起来的信号。"

    lines = [opening]
    for topic in selected:
        lines.append(_topic_supporting_line(topic))

    if themes:
        bottom_line = f"Bottom line：如果只想抓大意，先盯住{themes[0]}这条线，今天的重点基本都绕着它展开。"
    else:
        bottom_line = "Bottom line：先看这些已经冒头的方向，比逐条追零散消息更省时间。"
    lines.append(bottom_line)
    return "\n".join(lines).strip()


async def _generate_xhs_tags(
    title: str, summary: str = "", count: int = 5
) -> List[str]:
    """用 LLM 为小红书内容生成中文话题标签。失败时回退到固定标签。"""
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        from app.llm import get_agent_llm

        llm = get_agent_llm("writer")
        prompt = (
            f"你是小红书话题标签专家。请根据以下 AI 领域内容，生成 {count} 个适合小红书的中文话题标签。\n\n"
            "【要求】\n"
            "1. 每个标签 2-6 个中文字，纯中文，不含英文、数字、特殊符号\n"
            "2. 标签必须是小红书上常见的热门话题词，如：人工智能、AI工具、科技趋势、效率提升、程序员日常 等\n"
            "3. 不要输出 # 号，只输出标签文字，用逗号分隔\n"
            "4. 不要输出任何解释\n\n"
            "【示例输出】\n"
            "人工智能,科技热点,效率神器,程序员,深度学习\n"
        )
        input_text = (
            f"标题：{title}\n摘要：{summary[:200]}" if summary else f"标题：{title}"
        )
        resp = await llm.ainvoke(
            [
                SystemMessage(content=prompt),
                HumanMessage(content=input_text),
            ]
        )
        raw = getattr(resp, "content", "")
        if isinstance(raw, list):
            raw = "".join(str(c) for c in raw)
        # 解析逗号/空格分隔的标签
        candidates = re.split(r"[,，\s]+", raw.strip())
        # 只保留纯中文标签
        tags = [
            t.strip().lstrip("#")
            for t in candidates
            if t.strip()
            and all("\u4e00" <= c <= "\u9fff" for c in t.strip().lstrip("#"))
        ]
        if tags:
            logger.info(f"[AiDailyPublish] LLM generated tags: {tags[:count]}")
            return tags[:count]
    except Exception as e:
        logger.warning(f"[AiDailyPublish] LLM tag generation failed: {e}")
    return FALLBACK_TAGS[:count]


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
    # 优先使用自定义标签（过滤为中文），否则用 LLM 生成
    if tags:
        pub_tags = [t for t in tags if t and any("\u4e00" <= c <= "\u9fff" for c in t)]
    else:
        pub_tags = []
    if not pub_tags:
        pub_tags = await _generate_xhs_tags(pub_title, pub_content)

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
                    sources=[
                        s.source
                        for s in (topic.sources or [])[:4]
                        if getattr(s, "source", None)
                    ],
                )
            elif ct == "daily-rank":
                from datetime import date as date_cls

                result = await card_render_client.render_daily_rank(
                    date=date_cls.today().isoformat(),
                    topics=[
                        {
                            "rank": 1,
                            "title": topic.title,
                            "score": topic.final_score,
                            "tags": (topic.tags or [])[:3],
                        }
                    ],
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
    return _compose_editorial_ranking_copy(date_text, topics)


async def _default_ranking_tags(
    topics: List[Any], custom_tags: Optional[List[str]] = None
) -> List[str]:
    """整榜发布标签：优先自定义，然后 LLM 生成，最后兜底固定标签。"""
    tags: List[str] = []
    for tag in custom_tags or []:
        cleaned = tag.strip().lstrip("#")
        if (
            cleaned
            and cleaned not in tags
            and any("\u4e00" <= c <= "\u9fff" for c in cleaned)
        ):
            tags.append(cleaned)
    if len(tags) < 5:
        # 用榜单前几个话题的标题拼接给 LLM 生成标签
        titles = " / ".join(t.title for t in (topics or [])[:5])
        ai_tags = await _generate_xhs_tags(f"AI热点榜单：{titles}", count=5 - len(tags))
        for t in ai_tags:
            if t not in tags:
                tags.append(t)
    return tags[:5]


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
            result = await card_render_client.render_title(
                title=title_text, emoji="📊", theme="sunset"
            )
            cards["title"] = result
        elif ct == "daily-rank":
            result = await card_render_client.render_daily_rank(
                date=ranking.date,
                title="AI 每日热点榜单",
                topics=[
                    _topic_to_rank_item(topic, idx)
                    for idx, topic in enumerate(topics, 1)
                ],
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
    final_tags = await _default_ranking_tags(topics, tags)

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
        publish_result.update(
            {
                "date": ranking.date,
                "limit": len(topics),
                "title": title_text,
            }
        )
    return publish_result
