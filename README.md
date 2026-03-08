# AIInSight

AIInSight 是一个面向 AI 领域内容生产的 evidence-first 工作台，提供两条主链路：

- `AI Daily`：聚合多源 AI 资讯，生成当日热点榜单
- `AI Topic Deep Dive`：输入任意 AI 话题，自动检索证据、运行多 Agent 分析、生成卡片并支持发布到小红书

当前默认部署只需要 `api + mcp + renderer` 三个服务，不再依赖登录容器。

## 当前实现

### 1. AI 单话题深挖

单话题分析已经切到 AI 来源驱动，而不是国内社媒平台抓取。

- 默认直接执行 `analyze_topic(topic, depth="standard", image_count=0)`
- 默认来源组：
  - `media`: `aibase`, `jiqizhixin`, `qbitai`, `techcrunch_ai`
  - `research`: `hf_papers`
  - `code`: `github_trending`
  - `community`: `hn`, `reddit`
- Reddit 只有在存在凭证时才启用；缺失时自动跳过，不会让任务失败
- 分析阶段默认不生图，卡片生成和发布是显式后处理步骤

### 2. AI Daily

AI Daily 会从配置的 AI 来源中并行采集、去重、打分、聚类，输出当天话题榜单。

当前 AI Daily 数据源包括：

- `aibase`
- `jiqizhixin`
- `qbitai`
- `github_trending`
- `producthunt_ai`
- `hf_papers`
- `techcrunch_ai`
- `hn`
- `reddit`

### 3. 检索策略

单话题检索当前采用“缓存复用 + 实时补全”的混合策略：

1. 先扫描最近几天的 AI Daily 缓存，复用已标准化的 `SourceItem`
2. 再按所选来源实时抓取或搜索补充证据
3. 对 Top-N URL 做正文抽取，构建统一 `EvidenceBundle`
4. 将 `EvidenceBundle` 注入 reporter / analyst / debater / writer

正文抽取主库为 `trafilatura`。若正文提取失败，则自动降级为标题 + 摘要，不中断分析。

## 核心能力

- 多来源 AI 证据检索
- 多 Agent 辩论式分析
- AI Daily 聚合、评分与聚类
- 统一卡片渲染
- 小红书发布
- MCP 工具调用
- 兼容 HTTP 直连调用

## 系统架构

### 服务

- `api`: FastAPI 后端，承载 AI Daily、单话题工作流、卡片和发布接口
- `mcp`: MCP 服务，对外暴露 `analyze_topic`、`get_ai_daily`、`generate_topic_cards`、`publish_to_xhs` 等工具
- `renderer`: Playwright 渲染服务，负责输出卡片 PNG 预览

### 单话题工作流

`source_retriever -> reporter -> analyst -> debater -> writer -> image_generator -> xhs_publisher`

说明：

- 默认 `image_count=0`，所以 `image_generator` 通常会直接跳过
- `publish_to_xhs` 推荐在分析完成、卡片准备好后显式调用

### 关键目录

- [`app`](/Volumes/Work/Projects/AIInSight/app)：后端主代码
- [`app/services`](/Volumes/Work/Projects/AIInSight/app/services)：工作流、采集器、缓存、发布等服务
- [`app/services/collectors`](/Volumes/Work/Projects/AIInSight/app/services/collectors)：各来源采集器
- [`opinion_mcp`](/Volumes/Work/Projects/AIInSight/opinion_mcp)：MCP 服务与工具定义
- [`renderer`](/Volumes/Work/Projects/AIInSight/renderer)：卡片渲染服务
- [`cache/ai_daily`](/Volumes/Work/Projects/AIInSight/cache/ai_daily)：AI Daily 缓存
- [`outputs`](/Volumes/Work/Projects/AIInSight/outputs)：分析 Markdown、卡片预览等输出目录

## 快速开始

### 方式一：Docker Compose

```bash
docker compose up -d
```

启动后默认端口：

- `api`: `8000`
- `renderer`: `3001`
- `mcp`: `18061`

### 方式二：本地开发

1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

2. 安装渲染器依赖

```bash
cd renderer
npm install
npx playwright install chromium
```

3. 配置环境变量

```bash
cp .env.example .env
```

4. 启动后端

```bash
uvicorn app.main:app --reload --port 8000
```

5. 启动渲染器

```bash
cd renderer
npm run dev
```

6. 启动 MCP

```bash
python -m opinion_mcp.server --host 0.0.0.0 --port 18061
```

## 必要环境变量

至少需要配置一组可用 LLM Key，例如：

- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEYS`
- `MOONSHOT_API_KEYS`
- `GEMINI_API_KEYS`

可选能力：

- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT`
  - 启用 Reddit 社区证据
- `VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY`
  - 启用 AI 生图
- `XHS_MCP_URL`
  - 启用小红书发布

## 主要接口

### MCP 工具

- `analyze_topic`
- `get_analysis_status`
- `get_analysis_result`
- `generate_topic_cards`
- `publish_to_xhs`
- `get_ai_daily`
- `analyze_ai_topic`
- `generate_ai_daily_cards`
- `publish_ai_daily`

### HTTP 接口

- `POST /api/analyze`
- `GET /api/status`
- `GET /api/result`
- `POST /api/ai-daily/collect`
- `GET /api/ai-daily/{topic_id}`
- `POST /api/ai-daily/{topic_id}/analyze`
- `POST /api/ai-daily/{topic_id}/cards`
- `POST /api/ai-daily/{topic_id}/publish`

## 当前约束

- 单话题深挖基于“近期 AI 来源语料 + 实时补全”，不是全网历史回溯搜索
- 单话题默认 source set 不包含 `producthunt_ai`
- `platform_radar` 卡片字段名仍被保留，但语义上已经用于来源分布
- 旧文档中如果仍出现 `opinion-analyzer`、`platforms` 或登录容器描述，应以当前 README 和 `ai-topic-analyzer` skill 为准

## 推荐使用方式

### 单话题

1. 调用 `analyze_topic`
2. 轮询 `get_analysis_status`
3. 获取 `get_analysis_result`
4. 按需调用 `generate_topic_cards`
5. 用户确认后调用 `publish_to_xhs`

### AI Daily

1. 调用 `get_ai_daily`
2. 选择话题后调用 `analyze_ai_topic`
3. 按需生成卡片
4. 用户确认后发布
