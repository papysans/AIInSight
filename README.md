# AIInSight

AIInSight 是一个面向 AI 领域内容生产的 evidence-first 工作台，提供两条主链路：

- `AI Daily`：聚合多源 AI 资讯，生成当日热点榜单
- `AI Topic Deep Dive`：输入任意 AI 话题，自动检索证据、运行多 Agent 分析、生成卡片并支持发布到小红书

当前默认部署只需要 `api + mcp + renderer` 三个服务，不再依赖登录容器。

## 当前实现

### 1. AI 单话题深挖

单话题分析已经切到 AI 来源驱动，而不是国内社媒平台抓取。

- 默认直接执行 `analyze_topic(topic, depth="standard", image_count=0)`
- 对话层建议先确认分析模式（`quick` / `standard` / `deep` / `自定义来源`）后再启动
- 默认来源组：
  - `media`: `aibase`, `jiqizhixin`, `qbitai`, `techcrunch_ai`
  - `research`: `hf_papers`
  - `code`: `github_trending`
  - `community`: `hn`, `reddit`
- Reddit 只有在存在凭证时才启用；缺失时自动跳过，不会让任务失败
- 分析阶段默认不生图，卡片生成和发布是显式后处理步骤
- 单话题默认卡片建议使用 `title + impact + radar + timeline`，`hot-topic` 更适合 AI Daily 单条热点

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

### 小红书发布依赖

AIInSight 当前默认把 `xiaohongshu-mcp` 作为**宿主机侧服务**运行，再由 Docker 内的 `api` / `mcp` 通过 `host.docker.internal:18060/mcp` 调用。

推荐做法：

1. 在宿主机启动 `./scripts/start-xhs-mcp.sh`
2. 保持 `docker-compose.yml` 里的 `XHS_MCP_URL=http://host.docker.internal:18060/mcp`
3. 用 `GET /api/xhs/status` 或 `validate_publish` 检查服务和登录状态
4. 可用 `./scripts/check-xhs-mcp.sh` 一键检查端口、登录状态和 cookies
5. 可用 `./scripts/open-xhs-login-qrcode.sh` 本地拉起二维码并扫码登录
6. 如果 XHS MCP 部署在云端，可用 `./scripts/login-xhs-cloud.sh --url https://<your-host>/mcp`
7. 如果你希望前端或 Agent 直接拿到二维码地址，可调用 `GET /api/xhs/login-qrcode`

说明：

- 当前仓库没有内置 `xiaohongshu-mcp` 二进制
- 启动脚本会优先查找你本机已有的安装或源码目录
- 首次登录仍建议在宿主机完成，不建议把这一步硬塞进 AIInSight 的 Docker 链路
- 二维码脚本默认请求 `http://127.0.0.1:18060/mcp`，如果 XHS MCP 已部署在云端，可先设置 `XHS_MCP_URL=https://<your-host>/mcp`
- 云端场景可直接运行 `./scripts/login-xhs-cloud.sh --host xhs.example.com`，脚本会在本机打开二维码，但实际登录态会写入远端 XHS MCP 所在环境
- 二维码图片默认保存在 `outputs/xhs_login/`
- 卡片预览图片默认保存在 `outputs/card_previews/`
- `GET /api/xhs/login-qrcode` 在本地默认会直接返回完整 URL，例如 `http://127.0.0.1:8000/api/xhs/login-qrcode/file/<filename>.png`
- AI Daily / Topic 卡片接口返回的 `image_url` 也会在本地默认补成完整 URL，例如 `http://127.0.0.1:8000/api/card-previews/<filename>.png`
- `CARD_PREVIEW_PUBLIC_BASE_URL` 用于覆盖卡片预览图的对外访问前缀，适合云端反向代理、独立文件域名或后续接入 OSS/CDN
- `XHS_LOGIN_QRCODE_PUBLIC_BASE_URL` 用于覆盖二维码图片的对外访问前缀，适合云端反向代理、独立文件域名或后续接入 OSS/CDN 时保持返回字段不变
- `PUBLIC_API_BASE_URL` 仍作为通用 API 公网前缀使用；如果未设置 `XHS_LOGIN_QRCODE_PUBLIC_BASE_URL`，二维码地址会回退到它
- `XHS_LOGIN_QRCODE_TIMEOUT_SECONDS` 控制获取二维码时等待上游 `xiaohongshu-mcp` 的超时时间，默认 `30` 秒
- AIInSight 会优先复用仍在有效期内的最近一张二维码，避免短时间内重复向 `xiaohongshu-mcp` 请求导致卡死或超时
- 当前这一步只解决“返回完整可访问地址”，还没有把二维码文件上传到 OSS；后续接 OSS 时，可以在保留 `qr_image_url` 字段不变的前提下补上传逻辑

### 可选：XHS sidecar 模式

如果你想研究把 `xiaohongshu-mcp` 也挂进 Docker，而不替换当前稳定路径，可以使用额外的 compose overlay：

```bash
docker compose -f docker-compose.yml -f docker-compose.xhs.yml up -d
```

这个 overlay 会：

- 新增 `xhs-mcp` sidecar 容器
- 把 `api` / `mcp` 的 `XHS_MCP_URL` 从宿主机地址改成 `http://xhs-mcp:18060/mcp`
- 把 cookies 和上传图片挂到 `./runtime/xhs/data` 与 `./runtime/xhs/images`

注意：

- 这是可选实验路径，不替换当前宿主机启动方案
- 首次登录仍需要人工完成，建议通过上游工具或 MCP Inspector 获取二维码并登录
- 也可以直接在本机运行 `./scripts/open-xhs-login-qrcode.sh` 拉起二维码
- 默认显式指定 `linux/amd64`，在 Apple Silicon 上通常依赖 Docker Desktop 的架构兼容层

Apple Silicon 额外说明：

- 上游 `xpzouying/xiaohongshu-mcp:latest-arm64` 当前我实测会因为浏览器自动下载失败而直接返回 `500`
- 如果你希望继续走 Docker sidecar，又不想依赖 `linux/amd64` 模拟层，可运行 `./scripts/build-xhs-mcp-image.sh`
- 这个脚本会直接拉取上游源码，本地构建一个 `Debian + Chromium` 的 ARM64 修正版镜像
- 构建完成后可这样切换：

```bash
XHS_MCP_IMAGE=aiinsight-xhs-mcp:arm64-patched \
XHS_MCP_PLATFORM=linux/arm64 \
XHS_MCP_BROWSER_BIN=/usr/bin/chromium \
XHS_MCP_SOURCE_TIMEZONE=Asia/Shanghai \
docker compose -f docker-compose.yml -f docker-compose.xhs.yml up -d --force-recreate xhs-mcp api mcp
```

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

1. 先确认分析模式（默认 `standard`，可选 `quick` / `deep` / 自定义来源）
2. 调用 `analyze_topic`
3. 轮询 `get_analysis_status`
4. 获取 `get_analysis_result`
5. 按需调用 `generate_topic_cards`（默认 `title + impact + radar + timeline`）
6. 用户确认后调用 `publish_to_xhs`

### AI Daily

1. 调用 `get_ai_daily`
2. 选择话题后调用 `analyze_ai_topic`
3. 按需生成卡片
4. 用户确认后发布
