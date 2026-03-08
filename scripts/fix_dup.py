import sys

filepath = "/Volumes/Work/Projects/AIInSight/app/api/endpoints.py"

with open(filepath, "r") as f:
    content = f.read()

# Remove the second (English) duplicate block
old = """# ============================================================
# Topic Analysis Card Generation
# ============================================================

@router.post("/topic/cards")
async def topic_cards(request: TopicCardsRequest):
    \"\"\"Generate visual cards for topic analysis results\"\"\"
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

if old in content:
    content = content.replace(old, "", 1)
    with open(filepath, "w") as f:
        f.write(content)
    print("OK: duplicate removed")
else:
    print("ERROR: duplicate block not found")
    sys.exit(1)
