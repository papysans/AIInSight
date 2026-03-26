# AI Daily Ranking Render Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render today's AI daily ranking into Xiaohongshu-ready cover and ranking images using the repository's existing card renderer.

**Architecture:** Reuse the already running `renderer` and `mcp` services instead of adding any new rendering code. Feed validated `title` and `daily-rank` payloads into the current render client so the existing preview persistence layer writes PNG files into `outputs/card_previews/`.

**Tech Stack:** Python, Opinion MCP render client, Playwright renderer, Docker Compose

---

### Task 1: Prepare render payloads and run renderer

**Files:**
- Reference: `.agents/skills/shared/GUIDELINES.md`
- Reference: `opinion_mcp/tools/render.py`
- Reference: `opinion_mcp/services/card_render_client.py`

- [ ] **Step 1: Build a valid `title` payload**

```json
{
  "title": "AI 今日热点",
  "emoji": "🤖",
  "theme": "warm"
}
```

- [ ] **Step 2: Build a valid `daily-rank` payload**

```json
{
  "date": "2026-03-25",
  "title": "AI 每日热点",
  "topics": [
    {"rank": 1, "title": "OpenAI 关停 Sora", "score": 8.8, "tags": ["OpenAI", "视频生成"]},
    {"rank": 2, "title": "Claude Code 获得更高自主权", "score": 8.6, "tags": ["Anthropic", "Agent"]},
    {"rank": 3, "title": "月之暗面判断 AI 研发进入 AI 主导阶段", "score": 8.4, "tags": ["Kimi", "AI研发"]},
    {"rank": 4, "title": "千问上线 AI 打车", "score": 8.1, "tags": ["阿里", "Agent应用"]},
    {"rank": 5, "title": "Meta 推进 AI 电商", "score": 8.0, "tags": ["Meta", "AI电商"]},
    {"rank": 6, "title": "Spotify 拦截 AI 垃圾音乐冒名", "score": 7.9, "tags": ["Spotify", "内容治理"]},
    {"rank": 7, "title": "Kleiner Perkins 新募 35 亿美元继续押注 AI", "score": 7.8, "tags": ["VC", "AI投资"]},
    {"rank": 8, "title": "Databricks 收购两家初创公司强化 AI 安全", "score": 7.7, "tags": ["Databricks", "AISecurity"]},
    {"rank": 9, "title": "闲鱼 AI 相机 5 秒完成上架", "score": 7.6, "tags": ["电商", "AIGC"]},
    {"rank": 10, "title": "GitHub 热榜仍由 AI 开源生态主导", "score": 7.5, "tags": ["GitHub", "开源"]}
  ]
}
```

- [ ] **Step 3: Check renderer availability first**

Run:

```bash
python - <<'PY'
import asyncio
from opinion_mcp.services.card_render_client import card_render_client

async def main():
    print(await card_render_client.is_available())

asyncio.run(main())
PY
```

Expected: prints `True`

- [ ] **Step 4: Run the renderer through the existing MCP render flow**

Run:

```bash
python - <<'PY'
import asyncio, json
from opinion_mcp.tools.render import render_cards

SPECS = [
    {
        "card_type": "title",
        "payload": {
            "title": "AI 今日热点",
            "emoji": "🤖",
            "theme": "warm"
        }
    },
    {
        "card_type": "daily-rank",
        "payload": {
            "date": "2026-03-25",
            "title": "AI 每日热点",
            "topics": [
                {"rank": 1, "title": "OpenAI 关停 Sora", "score": 8.8, "tags": ["OpenAI", "视频生成"]},
                {"rank": 2, "title": "Claude Code 获得更高自主权", "score": 8.6, "tags": ["Anthropic", "Agent"]},
                {"rank": 3, "title": "月之暗面判断 AI 研发进入 AI 主导阶段", "score": 8.4, "tags": ["Kimi", "AI研发"]},
                {"rank": 4, "title": "千问上线 AI 打车", "score": 8.1, "tags": ["阿里", "Agent应用"]},
                {"rank": 5, "title": "Meta 推进 AI 电商", "score": 8.0, "tags": ["Meta", "AI电商"]},
                {"rank": 6, "title": "Spotify 拦截 AI 垃圾音乐冒名", "score": 7.9, "tags": ["Spotify", "内容治理"]},
                {"rank": 7, "title": "Kleiner Perkins 新募 35 亿美元继续押注 AI", "score": 7.8, "tags": ["VC", "AI投资"]},
                {"rank": 8, "title": "Databricks 收购两家初创公司强化 AI 安全", "score": 7.7, "tags": ["Databricks", "AISecurity"]},
                {"rank": 9, "title": "闲鱼 AI 相机 5 秒完成上架", "score": 7.6, "tags": ["电商", "AIGC"]},
                {"rank": 10, "title": "GitHub 热榜仍由 AI 开源生态主导", "score": 7.5, "tags": ["GitHub", "开源"]}
            ]
        }
    }
]

async def main():
    result = await render_cards(SPECS)
    print(json.dumps(result, ensure_ascii=False, indent=2))

asyncio.run(main())
PY
```

Expected: JSON output containing two successful render results with `output_path`. The spec input uses `daily-rank`, and the existing MCP/client flow normalizes it to `daily_rank` internally.

- [ ] **Step 5: Verify output files exist**

Run:

```bash
python - <<'PY'
import asyncio
from pathlib import Path
from opinion_mcp.tools.render import render_cards

SPECS = [
    {
        "card_type": "title",
        "payload": {"title": "AI 今日热点", "emoji": "🤖", "theme": "warm"},
    },
    {
        "card_type": "daily-rank",
        "payload": {
            "date": "2026-03-25",
            "title": "AI 每日热点",
            "topics": [
                {"rank": 1, "title": "OpenAI 关停 Sora", "score": 8.8, "tags": ["OpenAI", "视频生成"]},
                {"rank": 2, "title": "Claude Code 获得更高自主权", "score": 8.6, "tags": ["Anthropic", "Agent"]},
                {"rank": 3, "title": "月之暗面判断 AI 研发进入 AI 主导阶段", "score": 8.4, "tags": ["Kimi", "AI研发"]},
                {"rank": 4, "title": "千问上线 AI 打车", "score": 8.1, "tags": ["阿里", "Agent应用"]},
                {"rank": 5, "title": "Meta 推进 AI 电商", "score": 8.0, "tags": ["Meta", "AI电商"]},
                {"rank": 6, "title": "Spotify 拦截 AI 垃圾音乐冒名", "score": 7.9, "tags": ["Spotify", "内容治理"]},
                {"rank": 7, "title": "Kleiner Perkins 新募 35 亿美元继续押注 AI", "score": 7.8, "tags": ["VC", "AI投资"]},
                {"rank": 8, "title": "Databricks 收购两家初创公司强化 AI 安全", "score": 7.7, "tags": ["Databricks", "AISecurity"]},
                {"rank": 9, "title": "闲鱼 AI 相机 5 秒完成上架", "score": 7.6, "tags": ["电商", "AIGC"]},
                {"rank": 10, "title": "GitHub 热榜仍由 AI 开源生态主导", "score": 7.5, "tags": ["GitHub", "开源"]}
            ]
        },
    },
]

async def main():
    result = await render_cards(SPECS)
    for item in result["results"]:
        path = item.get("output_path")
        print(item["card_type"], path, Path(path).exists() if path else False)

asyncio.run(main())
PY
```

Expected: both output paths exist on disk, typically under `outputs/card_previews/_default/`

### Task 2: Report generated artifacts

**Files:**
- Output: `outputs/card_previews/...png`

- [ ] **Step 1: Capture final output paths**

List the generated `title` and `daily-rank` file paths.

- [ ] **Step 2: Relay concise status to the user**

Report whether both images rendered successfully and where they were saved.
