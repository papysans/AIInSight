---
name: ai-insight
description: AI 日报助手 - 从 7+ 数据源采集 AI 领域热点，生成日报榜单和分析卡片，并可发布到小红书。当用户提到"AI日报"、"AI热点"、"今日AI"、"tech daily"、"AI榜单"时使用此技能。
homepage: https://github.com/user/GlobalInSight
metadata: { "clawdbot": { "emoji": "🤖", "os": ["darwin", "linux", "win32"] } }
---

# 🤖 AI Insight - AI 日报助手

从 AIbase、机器之心、量子位、GitHub Trending、Hugging Face Papers、TechCrunch、Hacker News、Reddit 等数据源自动采集 AI 领域热点新闻，经评分聚合后生成结构化日报，并支持深度分析与卡片生成。

## 🐳 Docker 运行前置检查

如果当前任务涉及小红书发布、二维码登录、`check_xhs_status`、`publish_ai_daily`、`publish_ai_daily_ranking`，默认先假设 AIInSight 运行在 **main 分支四容器栈** 上：

- `api` (`8000`)
- `mcp` (`18061`)
- `renderer` (`3001`)
- `xhs-mcp` (`18060`)

优先建议或执行：

```bash
docker compose up -d --build api mcp renderer xhs-mcp
docker compose ps
docker compose logs --tail=60 mcp
```

如果 `api` 报 `8000` 端口被占，优先排查旧 worktree 项目的残留容器；如果 `mcp` 不通，优先看 `mcp` 日志而不是只盯 `xhs-mcp`。

---

## ⚠️ 关键行为规则

### 🟢 MUST DO

| # | 规则 | 说明 |
|---|------|------|
| **M0** | **优先使用缓存** | 调用 `get_ai_daily` 时默认不传 `force_refresh`，除非用户明确要求刷新 |
| **M1** | **展示榜单摘要** | 获取日报后，以排序列表形式展示 Top 话题，包含标题、来源数、标签 |
| **M2** | **深度分析前确认** | 用户选择话题做深度分析时，确认分析深度（quick/standard/deep） |
| **M3** | **卡片生成后展示** | 调用卡片生成后，告知用户已生成哪些类型的卡片，并优先展示每张预览图的 `image_url`；若没有再回退到 `output_path` |
| **M4** | **发布前必须确认** | 发布到小红书前必须获得用户明确确认 |
| **M5** | **发布时优先复用现有卡片** | 如果用户已经生成过卡片，发布时沿用同一话题和卡片类型，避免重复生成 |
| **M6** | **未登录时引导官方二维码登录** | 若发布链路提示未登录，先调用 `check_xhs_status` 确认，再按「小红书登录流程」章节引导用户获取二维码并扫码 |
| **M7** | **Docker-first 排障优先看 mcp 日志** | 如果用户反馈 18061 不通或发布链路异常，优先检查 `docker compose logs --tail=60 mcp`，确认 MCP Server 是否真正完成启动 |

### 🔴 MUST NOT DO

| # | 规则 | 说明 |
|---|------|------|
| **N0** | **不要每次都 force_refresh** | 采集需要请求多个外部站点，频繁刷新会被限流 |
| **N1** | **不要跳过展示步骤** | 不能拿到日报后不展示就直接分析 |
| **N2** | **不要自动发布** | 不能未经用户确认就发布到任何平台 |
| **N3** | **不要再引导 Cookie 注入作为默认登录方式** | 当前支持的公开登录流程以 `check_xhs_status` + `get_xhs_login_qrcode` 为主，不要继续把 Cookie 注入写成默认操作 |

---

## � 小红书登录流程

当前支持的公开登录流程以官方二维码登录为主；对于无法直接显示图片的客户端，需要把二维码 URL / route / file path 告知用户手动打开。

### 流程

1. **检查状态** — 调用 `check_xhs_status`，若已登录则跳过
2. **获取二维码** — 调用 `get_xhs_login_qrcode`
3. **展示二维码**
   - 若客户端能直接显示图片，则提示用户用小红书 App 扫码
   - 若客户端不能直接显示图片，则告知用户打开返回的 `qr_image_url`、`qr_image_route` 或 `qr_image_path`
4. **确认结果** — 用户扫码后，再次调用 `check_xhs_status`；若已登录则告知用户登录成功
5. **失败处理** — 若二维码超时或状态仍未登录，则重新调用 `get_xhs_login_qrcode`

### 注意事项
- 二维码有时效性，过期后需要重新获取
- 对于 OpenCode / Claude Code 等无法稳定显示图片的客户端，优先把可访问的二维码 URL 或文件路径返回给用户
- 如果 `mcp` 容器日志出现 `ImportError: cannot import name 'reset_xhs_login' from 'opinion_mcp.tools'`，说明镜像需要重新 `--build`，而不是继续重试调用工具

---

## �📋 主命令

### 1. `/ai-daily` — 获取今日 AI 热点日报

```
用户: 今日AI有什么热点？

助手:
🤖 AI 日报 - 2026-01-30

📊 Top 10 AI 热点:
1. 🔥 DeepSeek R2 正式发布 — 3个来源 | #LLM #开源
2. 📈 OpenAI GPT-5 传闻升温 — 2个来源 | #GPT #OpenAI
3. 🧪 Hugging Face 新论文：... — 2个来源 | #论文 #NLP
...

数据源: aibase, jiqizhixin, github_trending, hf_papers
采集时间: 2026-01-30 10:23:45

💡 输入话题编号可进行深度分析，如 "分析 1"
```

**参数**:
- `--refresh` → 传 `force_refresh=true`
- `--sources aibase,github_trending` → 仅使用指定源
- `--top N` → 只展示前 N 条

### 2. `/analyze <topic_or_id>` — 深度分析指定话题

```
用户: 分析 1

助手: 准备对 "DeepSeek R2 正式发布" 进行深度分析。

🔍 分析深度选择:
  ⚡ quick — 快速概览，约1分钟
  📋 standard — 标准分析（推荐），约3分钟
  🔬 deep — 深度研究，约5分钟

请选择深度，或回复"默认"使用 standard。
```

用户确认后：
1. 调用 `analyze_ai_topic(topic_id, depth)`
2. 展示分析结果（观点摘要、多角度解读、趋势判断）
3. 如生成了卡片预览，优先展示卡片访问地址 `image_url`；若没有再展示本地文件路径
4. 询问是否生成卡片或发布

### 3. `/publish <topic_or_id>` — 发布到小红书

发布前必须先确认。优先使用已有话题和卡片，不要重新采集。

```
用户: 把第 1 条做成小红书并发布

助手:
准备将 "DeepSeek R2 正式发布" 生成小红书图文并发布。

默认会生成:
- 标题卡
- 热点详情卡

请确认是否继续发布。回复“确认发布”后我再执行。
```

确认后：
1. 如尚未生成卡片，调用 `generate_ai_daily_cards(topic_id, card_types)`
2. 若返回了 `image_url`，优先把完整地址展示给用户；若没有再回退到 `output_path`
3. 调用 `publish_ai_daily(topic_id, card_types)`
4. 如果返回未登录，按「小红书登录流程」章节引导用户获取二维码并扫码，完成后再继续发布
5. 发布成功时返回结果与笔记链接

### 4. `/publish-today` — 将今天整榜做成小红书图文

当用户要求“把今天的榜单做成小红书图文”或“把今日榜单发布到小红书”时：
1. 先确认是“先生成预览”还是“直接发布”
2. 生成预览时调用 `generate_ai_daily_ranking_cards(limit, card_types)`
3. 若返回了 `image_url`，必须优先把每张榜单卡片的完整访问地址展示给用户；若没有再回退到 `output_path`
4. 发布时调用 `publish_ai_daily_ranking(limit, card_types)`
5. 默认卡片使用 `["title", "daily-rank"]`
6. 发布前必须再次确认
7. 如果未登录，按「小红书登录流程」章节引导用户获取二维码并扫码

---

## 🔧 MCP 工具参考

### get_ai_daily
获取今日 AI 日报。
```json
{
  "force_refresh": false,
  "sources": ["aibase", "jiqizhixin", "qbitai", "github_trending", "producthunt_ai", "hf_papers", "techcrunch_ai"]
}
```

### analyze_ai_topic
对日报话题运行深度分析。
```json
{
  "topic_id": "topic_xxx",
  "depth": "standard"
}
```

### generate_ai_daily_cards
生成可视化卡片。
```json
{
  "topic_id": "topic_xxx",
  "card_types": ["title", "hot-topic"]
}
```

### publish_ai_daily
将 AI 日报话题发布到小红书。
```json
{
  "topic_id": "topic_xxx",
  "card_types": ["title", "hot-topic"]
}
```

### check_xhs_status
检查小红书 MCP 可用性和登录状态。
```json
{}
```

### get_xhs_login_qrcode
获取小红书登录二维码。
```json
{}
```

若客户端无法直接展示图片，必须优先把 `qr_image_url`、`qr_image_route` 或 `qr_image_path` 告知用户，让用户手动打开二维码后扫码。

### generate_ai_daily_ranking_cards
为今日 AI 热点整榜生成榜单卡片。
```json
{
  "limit": 10,
  "card_types": ["title", "daily-rank"]
}
```

### publish_ai_daily_ranking
将今日 AI 热点整榜发布到小红书。
```json
{
  "limit": 10,
  "card_types": ["title", "daily-rank"]
}
```

---

## 🗺️ 数据源说明

| 数据源 | 语言 | 类型 | 说明 |
|--------|------|------|------|
| aibase | zh | 新闻 | AIbase.com AI 资讯 |
| jiqizhixin | zh | 新闻 | 机器之心行业报道 |
| qbitai | zh | 新闻 | 量子位科技报道 |
| github_trending | en | 代码仓库 | GitHub 每日趋势项目 |
| producthunt_ai | en | 产品 | Product Hunt AI 标签产品 |
| hf_papers | en | 论文 | Hugging Face 每日论文精选 |
| techcrunch_ai | en | 新闻 | TechCrunch AI 报道 |
