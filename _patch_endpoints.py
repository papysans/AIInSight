#!/usr/bin/env python3
"""Patch endpoints.py to add /topic/cards endpoint."""

filepath = "app/api/endpoints.py"

with open(filepath, "r") as f:
    content = f.read()

marker = "# ============================================================\n# AI Daily Pipeline API\n# ============================================================"

insert_block = """# ============================================================
# 话题分析卡片生成
# ============================================================

@router.post("/topic/cards")
async def topic_cards(request: TopicCardsRequest):
    \"\"\"为话题分析结果生成可视化卡片\"\"\"
    cards = {}
    for ct in request.card_types:
        if ct == "title":
            result = await card_render_client.render_title(title=request.title)
            cards["title"] = CardRenderResponse(**result)
        elif ct == "hot-topic":
            result = await card_render_client.render_hot_topic(
                title=request.title,
                summary=request.summary,
                tags=request.tags[:6],
                source_count=request.source_count,
                score=request.score,
                sources=request.sources[:4],
            )
            cards["hot-topic"] = CardRenderResponse(**result)
    return {"cards": cards}


"""

if marker in content:
    content = content.replace(marker, insert_block + marker, 1)
    with open(filepath, "w") as f:
        f.write(content)
    print("OK: /topic/cards endpoint inserted")
else:
    print("ERROR: marker not found in", filepath)
