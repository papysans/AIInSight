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
| **M6** | **发布前先检查登录，扫码后立即发布** | 发布流程开始时先调用 `check_xhs_status`；若未登录则立即获取二维码让用户扫码；扫码后**立刻执行发布**，不要在扫码和发布之间插入任何等待步骤（登录态仅在内存中，延迟会丢失） |
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

当前支持的公开登录流程以官方二维码登录为主。**登录态不稳定**（xhs-mcp 扫码后 cookies 不一定落盘），所以**必须在发布前紧挨着做登录检查，扫码后立即发布，中间不要有等待或容器重启**。

### ⚡ 核心原则：登录 → 立即发布，不能断开

xhs-mcp 的 QR 扫码登录态只保存在 headless browser 内存中，不会自动持久化到 cookies.json。这意味着：
- 扫码成功后，browser session 是活的，可以立即发布
- 但如果中间有任何延迟（用户犹豫、容器重启、session 超时），登录态就丢了
- **所以：在发布流程里，先检查登录 → 如果需要扫码就立刻扫 → 扫完立刻发布，一气呵成**

### 流程

1. **检查状态** — 调用 `check_xhs_status`，若已登录则跳过
2. **获取二维码** — 调用 `get_xhs_login_qrcode`
3. **展示二维码**（按优先级）
   - **终端 ASCII QR 码**：响应中的 `qr_ascii` 字段包含 Unicode 半块字符二维码，CLI 用户可直接用手机对准终端扫描
   - **浏览器预览页**：`qr_preview_url`（如 `http://localhost:8000/api/xhs/login-qrcode/preview`）— 带倒计时的 HTML 页面
   - **图片直链**：`qr_image_url` — 浏览器打开直接显示 PNG
   - **本地文件**：`qr_image_path` — 宿主机可 `open` 打开
4. **用户扫码后立即行动** — 不要等用户说"扫好了"再去 check_xhs_status 然后再发布。**应该直接调用发布接口**，因为 publish 内部会再次检查登录态
5. **失败处理** — 若二维码超时或发布仍返回未登录，则重新获取二维码并重复

### 注意事项
- 二维码有效期约 4 分钟，过期后需要重新获取
- 对于 OpenCode / Claude Code 等 CLI 客户端，**优先展示 `qr_ascii`（终端直接扫码）和 `qr_preview_url`（浏览器预览页）**
- 如果 `mcp` 容器日志出现 `ImportError`，说明镜像需要重新 `--build`
- **不要在扫码和发布之间插入不必要的等待步骤**

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

确认后（**登录检查前置，卡片生成和发布紧挨**）：
1. **先检查登录** — 调用 `check_xhs_status`
2. **未登录则立即引导扫码** — 调用 `get_xhs_login_qrcode`，展示 ASCII QR / 预览页 / 图片链接，等用户扫码
3. **用户扫码后立即执行后续步骤，不要再单独 check_xhs_status**
4. 如尚未生成卡片，调用 `generate_ai_daily_cards(topic_id, card_types)`
5. 若返回了 `image_url`，优先展示给用户
6. **立即调用** `publish_ai_daily(topic_id, card_types)` — 不能有间隔
7. 发布成功时返回结果与笔记链接
8. 若发布仍返回未登录，重新获取二维码并重复步骤 2-7

### 4. `/publish-today` — 将今天整榜做成小红书图文

当用户要求“把今天的榜单做成小红书图文”或“把今日榜单发布到小红书”时：
1. 先确认是“先生成预览”还是“直接发布”
2. **先检查登录** — 调用 `check_xhs_status`
3. **未登录则立即引导扫码** — 调用 `get_xhs_login_qrcode`，展示 ASCII QR / 预览页，等用户扫码
4. **用户扫码后不要再单独 check，直接往下走**
5. 生成预览时调用 `generate_ai_daily_ranking_cards(limit, card_types)`
6. 若返回了 `image_url`，必须优先把每张榜单卡片的完整访问地址展示给用户
7. **立即调用** `publish_ai_daily_ranking(limit, card_types)` — 不能有间隔
8. 默认卡片使用 `["title", "daily-rank"]`
9. 发布前必须再次确认
10. 若发布仍返回未登录，重新获取二维码并重复步骤 3-7

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

响应包含多种展示方式：
- `qr_ascii` — 终端 ASCII 二维码（CLI 用户直接对准手机扫描）
- `qr_preview_url` — 浏览器预览页 URL（带倒计时）
- `qr_image_url` — PNG 图片直链
- `qr_image_path` — 宿主机本地文件路径

**优先展示 `qr_ascii` 和 `qr_preview_url`**，适配 CLI 客户端无法渲染图片的场景。

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
