import sys

filepath = "/Volumes/Work/Projects/AIInSight/app/api/endpoints.py"

with open(filepath, "r") as f:
    content = f.read()

marker = "# AI Daily Pipeline API"

insert = '''# ============================================================
# Topic Analysis Card Generation
# ============================================================

@router.post("/topic/cards")
async def topic_cards(request: TopicCardsRequest):
    """Generate visual cards for topic analysis results"""
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


'''

idx = content.find(marker)
if idx == -1:
    print("ERROR: marker not found")
    sys.exit(1)

# Find the start of the line containing the marker (go back to the # ==== line before it)
line_start = content.rfind("# ====", 0, idx)
content = content[:line_start] + insert + content[line_start:]

with open(filepath, "w") as f:
    f.write(content)

print("OK: /topic/cards endpoint inserted")
