"""
AI News Scorer
Scores SourceItems by relevance, impact, freshness, and discussion metrics.
"""

from datetime import datetime, timezone
from typing import List
from loguru import logger

from app.schemas import SourceItem


# Keywords that boost AI relevance score
_AI_KEYWORDS = {
    "high": [
        "llm", "gpt", "claude", "gemini", "transformer", "diffusion",
        "agent", "rag", "fine-tune", "finetune", "lora", "rlhf",
        "大模型", "大语言模型", "智能体", "多模态", "推理模型",
    ],
    "medium": [
        "ai", "ml", "deep learning", "machine learning", "neural",
        "人工智能", "机器学习", "深度学习", "神经网络",
        "openai", "deepseek", "anthropic", "meta ai", "google ai",
    ],
}


def score_ai_relevance(item: SourceItem) -> float:
    """Score 0-10 for AI relevance based on title + summary keywords."""
    text = f"{item.title} {item.summary or ''}".lower()
    score = 3.0  # base score (item came from an AI-focused source)

    for kw in _AI_KEYWORDS["high"]:
        if kw in text:
            score += 2.0
    for kw in _AI_KEYWORDS["medium"]:
        if kw in text:
            score += 1.0

    # Source type bonus
    if item.source_type == "research":
        score += 1.0

    return min(10.0, score)


def score_freshness(item: SourceItem) -> float:
    """Score 0-10 based on publication time proximity."""
    if not item.published_at:
        return 5.0  # unknown = neutral
    try:
        pub = datetime.fromisoformat(item.published_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        hours_ago = (now - pub).total_seconds() / 3600
        if hours_ago < 6:
            return 10.0
        elif hours_ago < 12:
            return 8.0
        elif hours_ago < 24:
            return 6.0
        elif hours_ago < 48:
            return 4.0
        else:
            return 2.0
    except Exception:
        return 5.0


def score_items(items: List[SourceItem]) -> List[dict]:
    """
    Score a list of SourceItems.
    Returns list of dicts with item + scores, sorted by final_score desc.
    """
    scored = []
    for item in items:
        relevance = score_ai_relevance(item)
        freshness = score_freshness(item)
        # Placeholder: will be enriched by LLM or external signals in a future phase
        impact = 5.0
        discussion = 5.0

        final = relevance * 0.4 + freshness * 0.2 + impact * 0.25 + discussion * 0.15

        scored.append({
            "item": item,
            "ai_relevance_score": round(relevance, 1),
            "freshness_score": round(freshness, 1),
            "impact_score": round(impact, 1),
            "discussion_score": round(discussion, 1),
            "final_score": round(final, 1),
        })

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    logger.info(f"[AiNewsScorer] Scored {len(scored)} items, top score: {scored[0]['final_score'] if scored else 'N/A'}")
    return scored
