---
name: ai-insight
description: AI 日报助手 - 从 7+ 数据源采集 AI 领域热点，生成日报榜单和分析卡片，并可发布到小红书。当用户提到"AI日报"、"AI热点"、"今日AI"、"tech daily"、"AI榜单"时使用此技能。
homepage: https://github.com/user/GlobalInSight
metadata: { "clawdbot": { "emoji": "🤖", "os": ["darwin", "linux", "win32"] } }
---

# 🤖 AI Insight - AI 日报助手

从 AIbase、机器之心、量子位、GitHub Trending、Hugging Face Papers、TechCrunch、Hacker News、Reddit 等数据源自动采集 AI 领域热点新闻，经评分聚合后生成结构化日报，并支持深度分析与卡片生成。

## 远程 Gateway / 本地开发 两种运行模式

默认优先假设 AIInSight 运行在 **远程 MCP Gateway** 模式：

- 用户只连接一个远程 MCP 地址
- 使用 API key 标识独立 account
- 云端内部承载 `api + renderer + xhs-mcp`

只有在明确是本地开发 / 自托管场景时，才按四容器栈理解运行环境：

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
| **M6** | **发布前先检查登录并按 session 流程完成认证** | 发布流程开始时先调用 `check_xhs_status`；若未登录则获取二维码并保留 `session_id`；扫码后调用 `check_xhs_login_session`，若要求短信验证码则调用 `submit_xhs_verification`；确认登录成功后再发布 |
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

当前支持的公开登录流程以官方二维码登录为主，底层使用 `ShunL12324/xhs-mcp`。登录成功后会话会持久化到 SQLite，因此不再依赖旧的 `cookies.json` / 仅内存登录态模型。

### ⚡ 核心原则：登录和发布分离，发布仍是显式外部动作

当前链路分为三个阶段：
- 获取二维码：`get_xhs_login_qrcode` 返回二维码信息和 `session_id`
- 完成登录：`check_xhs_login_session(session_id)` 轮询状态；如需短信验证码，再调用 `submit_xhs_verification(session_id, code)`
- 执行发布：登录完成后，只有在用户明确确认的前提下才继续发布

登录状态会持久化到 sidecar 的 SQLite 数据库，容器重启后通常仍可恢复。

### 流程

1. **检查状态** — 调用 `check_xhs_status`，若已登录则跳过
2. **获取二维码** — 调用 `get_xhs_login_qrcode`，保留返回的 `session_id`
3. **展示二维码**（按优先级）
   - **终端 ASCII QR 码**：响应中的 `qr_ascii` 字段包含 Unicode 半块字符二维码，CLI 用户可直接用手机对准终端扫描
   - **浏览器预览页**：`qr_preview_url`（如 `http://localhost:8000/api/xhs/login-qrcode/preview`）— 带倒计时的 HTML 页面
   - **图片直链**：`qr_image_url` — 浏览器打开直接显示 PNG
   - **本地文件**：`qr_image_path` — 宿主机可 `open` 打开
4. **用户扫码后轮询登录状态** — 调用 `check_xhs_login_session(session_id)`
5. **如要求验证码** — 调用 `submit_xhs_verification(session_id, code)`
6. **登录成功后再继续发布链路**
7. **失败处理** — 若二维码超时、session 过期或登录失败，则重新获取二维码并重复

### 注意事项
- 二维码有效期约 4 分钟，过期后需要重新获取
- 对于 OpenCode / Claude Code 等 CLI 客户端，**优先展示 `qr_ascii`（终端直接扫码）和 `qr_preview_url`（浏览器预览页）**
- 如果 `mcp` 容器日志出现 `ImportError`，说明镜像需要重新 `--build`
- 不要再把 Cookie 注入或“扫码后只保存在内存”的旧模型当作默认心智
- 真实发布会创建外部内容，必须单独获得用户确认

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
1. 优先走 split path：`retrieve_and_report` → 宿主端 debate → `submit_analysis_result`
2. 如果当前客户端不支持宿主端 debate，再回退到 `analyze_ai_topic(topic_id, depth)`
3. 展示分析结果（观点摘要、多角度解读、趋势判断）
4. 如生成了卡片预览，优先展示卡片访问地址 `image_url`；若没有再展示本地文件路径
5. 询问是否生成卡片或发布

宿主端 debate 规则与 `ai-topic-analyzer` 保持一致：

- Analyst 先基于 `retrieve_and_report` 返回的 `news_content + source_stats` 输出第一版分析
- Debater 只负责反驳、补盲点和挑战推断
- Debater 明确回复 `PASS` 或达到 `max_rounds` 时结束
- 结束后调用 `submit_analysis_result`，把 `final_analysis + debate_history` 提交回云端后半段

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
1. **先检查登录** — 调用 `check_xhs_status`
2. **未登录则获取二维码** — 调用 `get_xhs_login_qrcode`，展示 ASCII QR / 预览页 / 图片链接，并保留 `session_id`
3. **用户扫码后轮询登录状态** — 调用 `check_xhs_login_session(session_id)`
4. **若要求验证码** — 调用 `submit_xhs_verification(session_id, code)`
5. 登录成功后，如尚未生成卡片，调用 `generate_ai_daily_cards(topic_id, card_types)`
6. 若返回了 `image_url`，优先展示给用户
7. **仅在用户确认发布后** 调用 `publish_ai_daily(topic_id, card_types)`
8. 发布成功时返回结果与笔记链接
9. 若 session 失效或登录失败，重新获取二维码并重复步骤 2-8

### 4. `/publish-today` — 将今天整榜做成小红书图文

当用户要求“把今天的榜单做成小红书图文”或“把今日榜单发布到小红书”时：
1. 先确认是“先生成预览”还是“直接发布”
2. **先检查登录** — 调用 `check_xhs_status`
3. **未登录则获取二维码** — 调用 `get_xhs_login_qrcode`，展示 ASCII QR / 预览页，并保留 `session_id`
4. **用户扫码后轮询登录状态** — 调用 `check_xhs_login_session(session_id)`
5. **若要求验证码** — 调用 `submit_xhs_verification(session_id, code)`
6. 生成预览时调用 `generate_ai_daily_ranking_cards(limit, card_types)`
7. 若返回了 `image_url`，必须优先把每张榜单卡片的完整访问地址展示给用户
8. 默认卡片使用 `["title", "daily-rank"]`
9. 发布前必须再次确认
10. 登录完成且用户确认后，再调用 `publish_ai_daily_ranking(limit, card_types)`

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
- `session_id` — 登录会话 ID，后续轮询 / 验证码提交流程必需

**优先展示 `qr_ascii` 和 `qr_preview_url`**，适配 CLI 客户端无法渲染图片的场景。

### check_xhs_login_session
轮询扫码登录状态。
```json
{
  "session_id": "sess_xxx"
}
```

### submit_xhs_verification
提交短信验证码完成登录。
```json
{
  "session_id": "sess_xxx",
  "code": "123456"
}
```

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
