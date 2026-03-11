# AI Insight 功能使用指南

> AI 日报 + AI 单话题深挖。当前实现同时支持 AI Daily 聚合榜单，以及面向任意 AI 话题的多来源证据检索、分析、卡片生成与发布。

---

## 目录

1. [功能概览](#功能概览)
2. [环境准备](#环境准备)
3. [快速开始](#快速开始)
4. [API 端点](#api-端点)
5. [MCP 工具](#mcp-工具)
6. [Copilot Skill 使用](#copilot-skill-使用)
7. [卡片渲染器](#卡片渲染器)
8. [Docker 部署](#docker-部署)
9. [配置说明](#配置说明)
10. [常见问题](#常见问题)

---

## 功能概览

AI Insight 模块提供以下核心功能：

| 功能 | 说明 |
|------|------|
| **AI 日报采集** | 同时从 AIbase、机器之心、量子位、GitHub Trending、Product Hunt、HF Papers、TechCrunch、HN、Reddit 采集 AI 领域内容 |
| **单话题深挖** | 输入任意 AI 话题，直接走默认 AI 来源组做 evidence-first 分析，不再要求选择平台 |
| **智能评分** | 基于 AI 相关性、时效性、影响力、讨论度四维打分 |
| **话题聚类** | 相似新闻自动聚合为话题，去重合并 |
| **深度分析** | 对单个话题运行多角度辩论式分析 |
| **卡片渲染** | 生成标题卡、排行榜卡等可视化图片 |
| **一键发布** | 卡片 + 文案自动发布到小红书 |

### 数据源

| 源名称 | 语言 | 类型 | 内容 |
|--------|------|------|------|
| `aibase` | 中文 | media | AI 新闻资讯 |
| `jiqizhixin` | 中文 | media | 机器之心文章/每日精选 |
| `qbitai` | 中文 | media | 量子位 AI 新闻 |
| `github_trending` | 英文 | code | GitHub 热门仓库 |
| `producthunt_ai` | 英文 | product | Product Hunt AI 产品 |
| `hf_papers` | 英文 | research | Hugging Face 热门论文 |
| `techcrunch_ai` | 英文 | media | TechCrunch AI 频道 |
| `hn` | 英文 | community | Hacker News 社区讨论 |
| `reddit` | 英文 | community | Reddit 社区讨论（需凭证） |

---

## 环境准备

### 1. Python 后端

```bash
# 要求 Python >= 3.9
pip install -r requirements.txt

# 配置环境变量 (.env)
cp .env.example .env
# 编辑 .env 填入 LLM API Key 等
```

### 2. 前端 + 渲染器

```bash
# 安装前端依赖
npm install

# 安装渲染器依赖
cd renderer && npm install && npx playwright install chromium
```

### 3. 启动服务

```bash
# 终端 1：启动后端 (8000)
uvicorn app.main:app --reload --port 8000

# 终端 2：启动前端 (5173)
npm run dev

# 终端 3：启动渲染器 (3001)
cd renderer && npm start
```

---

## 快速开始

### 一键采集 AI 日报

```bash
# 1. 采集（首次或强制刷新）
curl -X POST http://localhost:8000/api/ai-daily/collect \
  -H "Content-Type: application/json" \
  -d '{"force_refresh": true}'

# 2. 查看今日日报（使用缓存）
curl http://localhost:8000/api/ai-daily
```

返回示例：
```json
{
  "date": "2026-03-08",
  "topics": [
    {
      "topic_id": "cluster_abc123",
      "title": "DeepSeek R2 正式发布",
      "summary_zh": "DeepSeek 发布新一代推理模型...",
      "tags": ["deepseek", "llm", "推理"],
      "source_count": 3,
      "final_score": 8.2
    }
  ],
  "total": 15,
  "sources_used": ["aibase", "jiqizhixin", "qbitai", "github_trending", "hf_papers"]
}
```

### 指定数据源

```bash
curl -X POST http://localhost:8000/api/ai-daily/collect \
  -H "Content-Type: application/json" \
  -d '{"sources": ["github_trending", "hf_papers"]}'
```

### 深度分析某个话题

```bash
curl -X POST http://localhost:8000/api/ai-daily/cluster_abc123/analyze \
  -H "Content-Type: application/json" \
  -d '{"depth": "deep"}'
```

### 生成卡片

```bash
curl -X POST http://localhost:8000/api/ai-daily/cluster_abc123/cards \
  -H "Content-Type: application/json" \
  -d '{"card_types": ["title", "daily-rank"]}'
```

### 发布到小红书

```bash
curl -X POST http://localhost:8000/api/ai-daily/cluster_abc123/publish \
  -H "Content-Type: application/json" \
  -d '{"tags": ["AI日报", "科技"], "card_types": ["title", "daily-rank"]}'
```

---

## API 端点

所有端点前缀：`/api`

### 采集与查询

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/ai-daily/collect` | 触发采集 Pipeline (collect → score → cluster → cache) |
| `GET` | `/ai-daily` | 获取今日日报（优先读缓存） |
| `GET` | `/ai-daily/{topic_id}` | 获取单个话题详情 |

### 分析与卡片

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/ai-daily/{topic_id}/analyze` | 对话题运行深度分析 |
| `POST` | `/ai-daily/{topic_id}/cards` | 为话题生成可视化卡片 |
| `POST` | `/ai-daily/{topic_id}/publish` | 将话题发布到小红书 |

### 通用卡片渲染

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/cards/title` | 渲染标题卡 |
| `POST` | `/cards/radar` | 渲染雷达图卡 |
| `POST` | `/cards/timeline` | 渲染时间线卡 |
| `POST` | `/cards/trend` | 渲染趋势卡 |
| `POST` | `/cards/daily-rank` | 渲染排行榜卡 |

### 请求参数

#### `POST /ai-daily/collect`

```json
{
  "force_refresh": false,
  "sources": ["aibase", "jiqizhixin"]  // 可选，留空使用全部
}
```

#### `POST /ai-daily/{topic_id}/analyze`

```json
{
  "depth": "standard",    // "quick" | "standard" | "deep"
  "debate_rounds": 2,
  "image_count": 2,
  "with_cards": true
}
```

#### `POST /ai-daily/{topic_id}/cards`

```json
{
  "card_types": ["title", "daily-rank"]  // 可选类型：title, daily-rank, radar, timeline, trend
}
```

#### `POST /ai-daily/{topic_id}/publish`

```json
{
  "title": "自定义标题",      // 可选
  "content": "自定义正文",    // 可选
  "tags": ["AI", "科技"],    // 可选
  "card_types": ["title", "daily-rank"]
}
```

---

## MCP 工具

通过 Opinion MCP Server（默认端口 18061）暴露以下工具：

### `get_ai_daily`

获取今日 AI 日报。

```
参数：
  force_refresh: bool = false  — 是否强制刷新
  sources: string[] = null     — 指定数据源
```

### `analyze_ai_topic`

对日报话题深度分析。

```
参数：
  topic_id: string  — 话题 ID（必填）
  depth: "quick" | "standard" | "deep" = "standard"
```

### `generate_ai_daily_cards`

为话题生成卡片图片。

```
参数：
  topic_id: string   — 话题 ID（必填）
  card_types: string[] = ["title", "daily-rank"]
```

### `publish_ai_daily`

将话题发布到小红书。

```
参数：
  topic_id: string   — 话题 ID（必填）
  title: string      — 自定义标题
  content: string    — 自定义正文
  tags: string[]     — 标签列表
  card_types: string[] — 卡片类型
```

### 在 ClawdBot 中使用

```
用户: 帮我看看今天 AI 圈有什么新闻
→ ClawdBot 自动调用 get_ai_daily

用户: 第3个话题挺有趣，帮我深度分析一下
→ ClawdBot 自动调用 analyze_ai_topic(topic_id="cluster_xxx", depth="deep")

用户: 生成卡片发小红书
→ ClawdBot 自动调用 publish_ai_daily(topic_id="cluster_xxx")
```

---

## Copilot Skill 使用

在 VS Code Copilot Chat 中可以直接使用 AI Insight 技能。

### 触发关键词

- "AI日报"、"AI热点"、"今日AI"、"tech daily"、"AI榜单"

### 示例对话

```
你: @workspace 帮我生成今天的AI日报
Copilot: [调用 get_ai_daily] 今日共采集 18 个 AI 话题...

你: 帮我分析第一个话题并生成卡片
Copilot: [调用 analyze_ai_topic + generate_ai_daily_cards]

你: 发布到小红书
Copilot: [调用 publish_ai_daily]
```

---

## 卡片渲染器

渲染器由 3 层组成：

```
Python API  →  renderer/server.js (Express+Playwright)  →  前端渲染器 (Vue)
```

### 渲染流程

1. Python 调用 `CardRenderClient.render_daily_rank(date, topics, title)`
2. Client 发 POST 到 `http://renderer:3001/render/daily_rank`
3. renderer/server.js 用 Playwright 打开 `http://frontend:5173/render-cards`
4. 通过 `window.__CARD_RENDERER__.render(type, payload)` 渲染组件
5. Playwright 截图返回 base64 dataURL

### 排行榜卡数据格式

renderer 期望每个 topic 条目格式：
```json
{
  "rank": 1,
  "title": "DeepSeek R2 发布",
  "score": 8.2,
  "tags": ["llm", "推理"]
}
```

### 健康检查

```bash
curl http://localhost:3001/healthz
# 返回: { "status": "ok" }
```

---

## Docker 部署

### 使用 docker-compose

```bash
# main 分支推荐：重建并启动完整四容器栈
docker compose up -d --build api mcp renderer xhs-mcp

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

### 当前 Docker 栈

当前默认部署使用以下 **4 个容器**：

```bash
docker compose up -d api mcp renderer xhs-mcp
```

- `api`：FastAPI 后端，默认端口 `8000`
- `mcp`：MCP / 兼容 HTTP 服务，默认端口 `18061`
- `renderer`：Playwright 渲染服务，默认端口 `3001`
- `xhs-mcp`：小红书 sidecar，默认端口 `18060`

Reddit 仅在配置好凭证时启用；缺失时会自动跳过，不影响任务成功。

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| api | 8000 | FastAPI 后端 |
| renderer | 3001 | Playwright 截图服务 |
| mcp | 18061 | MCP / 兼容 HTTP 服务 |
| xhs-mcp | 18060 | 小红书 sidecar |

### 常见启动与排障

#### 先确认四个服务都起来了

```bash
docker compose ps
```

期望看到：`api / mcp / renderer / xhs-mcp` 都是 `Up`。

#### `api` 启动失败，提示 8000 端口被占用

症状：

```text
Bind for 0.0.0.0:8000 failed: port is already allocated
```

这通常表示旧的 worktree 项目容器还在占端口。先检查：

```bash
docker ps --format "table {{.Names}}\t{{.Ports}}"
```

然后停止旧的 `*-api-1` / `*-mcp-1` / `*-renderer-1` 容器，再重新执行四容器启动命令。

#### `mcp` 容器起不来

先看日志：

```bash
docker compose logs --tail=80 mcp
```

如果看到导入错误，例如：

```text
ImportError: cannot import name 'reset_xhs_login' from 'opinion_mcp.tools'
```

说明镜像没有带上最新代码，重新执行：

```bash
docker compose up -d --build api mcp renderer xhs-mcp
```

### 环境变量

在 `.env` 文件中配置：

```env
# LLM 配置
OPENAI_API_KEY=sk-xxx
# 或 GOOGLE_API_KEY=xxx

# 渲染器（Docker 内自动配置，本地开发用）
RENDERER_SERVICE_URL=http://localhost:3001
RENDERER_TIMEOUT=30
```

---

## 配置说明

### `app/config.py` 中的 `AI_DAILY_CONFIG`

```python
AI_DAILY_CONFIG = {
    "enabled": True,
    "cache_dir": "cache/ai_daily",       # 缓存目录
    "max_topics": 20,                     # 最大话题数
    "collect_interval_hours": 6,          # 采集间隔
    "renderer_service_url": "...",        # 渲染器地址
    "renderer_timeout": 30,              # 渲染超时(秒)
    "sources": {                          # 数据源开关
        "aibase": {"enabled": True, ...},
        "jiqizhixin": {"enabled": True, ...},
        # ...
    },
}
```

### 关闭某个数据源

在 `app/config.py` 中将对应 source 的 `enabled` 改为 `False`：

```python
"producthunt_ai": {"enabled": False, ...},
```

### AI 相关性阈值

在 `app/services/ai_daily_pipeline.py` 中 `AI_RELEVANCE_THRESHOLD = 3.0`，低于此分数的条目会在评分后被过滤。

### 评分权重

在 `app/services/ai_news_scorer.py` 中：

```
final = relevance × 0.4 + freshness × 0.2 + impact × 0.25 + discussion × 0.15
```

> 注意：`impact_score` 和 `discussion_score` 目前为固定值 5.0（占位），将在后续版本通过 LLM 或外部信号源丰富。

---

## 常见问题

### Q: 采集返回 0 条结果？

1. 检查网络连接（部分源需要科学上网）
2. 检查 config 中 source 是否 enabled
3. 用 `force_refresh: true` 跳过缓存
4. 查看后端日志中各 collector 的输出

### Q: 卡片渲染失败？

1. 确认渲染器服务已启动：`curl http://localhost:3001/healthz`
2. 确认前端服务已启动：`curl http://localhost:5173`
3. 检查 `RENDERER_SERVICE_URL` 配置正确

### Q: 发布到小红书失败？

1. 确认 XHS-MCP 服务已运行
2. 检查小红书登录 Cookie 是否有效
3. 使用 `validate_publish` MCP 工具诊断

### Q: 测试如何运行？

```bash
# 安装测试依赖
pip install pytest pytest-asyncio

# 运行所有测试
pytest tests/ -v

# 只跑 AI 日报相关测试
pytest tests/services/test_ai_news_scorer.py tests/services/test_ai_daily_pipeline.py tests/collectors/ -v
```

---

## 架构图

```
┌─────────────────────────────────────────────────────┐
│  Copilot Skill / MCP Tools / REST API               │
├─────────────────────────────────────────────────────┤
│  FastAPI Endpoints  (/api/ai-daily/*)               │
├─────────────────────────────────────────────────────┤
│  Pipeline                                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │Collectors│→│ Scorer   │→│ Cluster  │→│ Cache  │ │
│  │ (7 src)  │ │(4-dim)   │ │(bigram)  │ │(daily) │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────┘ │
├─────────────────────────────────────────────────────┤
│  Card Render Client  →  Renderer (Playwright)       │
│                          → Vue Renderers             │
├─────────────────────────────────────────────────────┤
│  Publish Service  →  XHS-MCP                        │
└─────────────────────────────────────────────────────┘
```
