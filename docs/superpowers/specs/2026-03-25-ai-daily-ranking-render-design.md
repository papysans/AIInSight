# AI Daily Ranking Render Design

## Goal

Render a Xiaohongshu-friendly daily ranking image set for today's AI hotspot roundup using the repository's existing `render_cards` flow and supported `title` + `daily-rank` card types.

## Scope

- Reuse the running renderer service and existing card payload contracts.
- Produce two ranking images: a cover card and a daily ranking card.
- Use today's manually curated ranking data as render input.

## Chosen Approach

Use the existing renderer stack instead of creating a new visual template. This keeps the work aligned with `opinion_mcp/tools/render.py`, `opinion_mcp/services/card_render_client.py`, and the payload contracts defined in `.agents/skills/shared/GUIDELINES.md`.

## Card Set

1. `title`
   - Title: `AI 今日热点`
   - Emoji: `🤖`
   - Theme: `warm`

2. `daily-rank`
   - Title: `AI 每日热点`
   - Date: `2026-03-25`
   - Topics: Top 10 ranking entries with rank, title, score, and tags

## Execution Notes

- Prefer direct use of the existing Python client or HTTP renderer path.
- Persist outputs to `outputs/card_previews/` through the current preview persistence logic.
- Verify rendered file paths after generation before reporting completion.
