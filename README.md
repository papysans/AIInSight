# AIInSight

AIInSight 是一个面向 AI 领域内容生产的 evidence-first 工作台，提供两条主链路：

- `AI Daily`：聚合多源 AI 资讯，生成当日热点榜单
- `AI Topic Deep Dive`：输入任意 AI 话题，自动检索证据、运行多 Agent 分析、生成卡片并支持发布到小红书

当前默认部署包含 `api + mcp + renderer + xhs-mcp` 四个服务，小红书能力走 Docker sidecar 主链路。

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

### 最快部署指南（推荐：Docker Compose）

这是当前仓库默认支持的主链路：**`api + mcp + renderer + xhs-mcp` 4 容器一起启动**。

#### 1. 复制环境变量模板

```bash
cp .env.example .env
```

#### 2. 至少填 1 组可用 LLM Key

打开 `.env`，至少配置下面任意一组：

- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEYS`
- `MOONSHOT_API_KEYS`
- `DOUBAO_API_KEYS`
- `ZHIPU_API_KEYS`
- `GEMINI_API_KEYS`

#### 3. 直接启动完整 Docker 栈

```bash
docker compose up -d --build api mcp renderer xhs-mcp
```

#### 4. 立即验证服务是否正常

```bash
docker compose ps
docker compose logs --tail=60 mcp
curl http://localhost:8000/api/health
curl http://localhost:18061/health
curl http://localhost:3001/healthz
```

如果一切正常，默认端口如下：

- `api`: `8000`
- `renderer`: `3001`
- `mcp`: `18061`
- `xhs-mcp`: `18060`

#### 5. 停止服务

```bash
docker compose down
```

#### 6. 首次在 OpenCode 中接入 MCP

如果你只是在本地把 AIInSight 服务跑起来，**到这一步已经够了**；`mcp` 服务会随 Docker 一起启动，并暴露在：

- `http://localhost:18061/health`
- `http://localhost:18061/mcp`

但如果你希望 **OpenCode 首次就能直接调用 `aiinsight-mcp`**，还需要在 OpenCode 客户端侧手动添加这个 MCP 服务。

推荐接入目标：

- MCP 名称：`aiinsight-mcp`
- MCP URL：`http://localhost:18061/mcp`

接入前建议先验证：

```bash
curl http://localhost:18061/health
curl http://localhost:18061/mcp
```

说明：

- `18061` 是 AIInSight 自己暴露给 OpenCode / Claude Code 一类客户端使用的 MCP 服务
- `18060` 是内部 `xhs-mcp` sidecar，默认给 `api` / `mcp` 容器走小红书链路使用，**不是首次在 OpenCode 中注册的目标地址**

#### Docker 部署说明

- 使用默认 `docker-compose.yml` 时，`api` / `mcp` 会自动通过容器网络访问 `http://xhs-mcp:18060/mcp`
- `.env.example` 里的 `XHS_MCP_URL=http://host.docker.internal:18060/mcp` 更适合宿主机直连或自定义部署；**走默认 Docker Compose 时会被 compose 内的 sidecar 地址覆盖**
- 如果你只想最快跑起来，优先使用上面的 4 容器命令，不需要再叠加历史 `docker-compose.xhs.yml`
- 如果是 Apple Silicon 且 `xhs-mcp` 镜像异常，可直接跳到下文的 “Apple Silicon 额外说明”

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
- `DOUBAO_API_KEYS`
- `ZHIPU_API_KEYS`
- `GEMINI_API_KEYS`

可选能力：

- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT`
  - 启用 Reddit 社区证据
- `VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY`
  - 启用 AI 生图
- `XHS_MCP_URL`
  - 非 Docker Compose / 自定义部署时启用小红书发布；默认 Docker Compose 会自动改用 `http://xhs-mcp:18060/mcp`

### 小红书发布依赖

AIInSight 当前支持的 XHS 发布链路是 **Docker sidecar 主链路**：`api` / `mcp` 通过容器网络访问 `http://xhs-mcp:18060/mcp`。

#### main 分支推荐启动方式

在仓库根目录、`main` 分支下，默认应把以下 **4 个容器** 一起拉起：

- `api` → `8000`
- `mcp` → `18061`
- `renderer` → `3001`
- `xhs-mcp` → `18060`

推荐命令：

```bash
docker compose up -d --build api mcp renderer xhs-mcp
```

启动后建议立刻检查：

```bash
docker compose ps
docker compose logs --tail=60 mcp
```

若 `mcp` 正常启动，日志里应能看到类似：

- `AIInSight MCP Server 启动`
- `服务地址: http://0.0.0.0:18061`
- `MCP 端点: http://0.0.0.0:18061/mcp`

推荐做法：

1. 优先运行 `docker compose up -d --build api mcp renderer xhs-mcp`
2. 使用 `GET /api/xhs/status` 或 `validate_publish` 检查 `xhs-mcp` sidecar 可用性和登录状态
3. 若未登录，调用 `/api/xhs/login-qrcode` 或 MCP `get_xhs_login_qrcode`
4. 如果客户端不能直接显示二维码，打开返回的 `qr_image_url`、`qr_image_route` 或 `qr_image_path`
5. 用小红书 App 扫码后，再次检查登录状态

说明：

- `xhs-mcp` 作为 Docker sidecar 挂在默认 compose 中，不再以宿主机进程作为支持主链路
- 登录二维码默认保存在 `outputs/xhs_login/`，并可通过 `/api/xhs/login-qrcode/file/<filename>` 访问
- 卡片预览图片默认保存在 `outputs/card_previews/`
- AI Daily / Topic 卡片接口返回的 `image_url` 也会在本地默认补成完整 URL，例如 `http://127.0.0.1:8000/api/card-previews/<filename>.png`
- `CARD_PREVIEW_PUBLIC_BASE_URL` 用于覆盖卡片预览图的对外访问前缀，适合云端反向代理、独立文件域名或后续接入 OSS/CDN
- `XHS_LOGIN_QRCODE_PUBLIC_BASE_URL` 可用于覆盖登录二维码的对外访问前缀，适合远程访问或反向代理
- 仓库里如果仍保留 cookie 上传或 Playwright 登录代理脚本，应视为迁移/内部排障能力，而不是当前支持的公开登录流程

常见排障：

- 如果 `api` 启动时报 `Bind for 0.0.0.0:8000 failed: port is already allocated`，通常是旧 worktree / 旧项目容器还占着 `8000`
- 可先用 `docker ps --format "table {{.Names}}\t{{.Ports}}"` 找到旧的 `*-api-1` / `*-mcp-1` / `*-renderer-1` 容器并停止，再重新执行四容器启动命令
- 如果 `mcp` 容器反复退出，优先检查：

```bash
docker compose logs --tail=80 mcp
```

- 若日志出现 `ImportError: cannot import name 'reset_xhs_login' from 'opinion_mcp.tools'` 一类错误，说明当前镜像没有带上最新代码，需要重新 `--build`

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
docker compose up -d --force-recreate api mcp renderer xhs-mcp
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
