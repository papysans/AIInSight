# AIInSight

AIInSight 是一个面向 AI 领域内容生产的 evidence-first 工作台，提供两条主链路：

- `AI Daily`：聚合多源 AI 资讯，生成当日热点榜单
- `AI Topic Deep Dive`：输入任意 AI 话题，自动检索证据、运行多 Agent 分析、生成卡片并支持发布到小红书

## 架构

当前为 **Skill-Driven 架构**：所有分析推理在宿主端 Skill（LLM）完成，云端 MCP Server 退化为 renderer + XHS 纯能力服务。

### 3 服务栈

| 服务 | 端口 | 说明 |
|------|------|------|
| `mcp` | 18061 | MCP 服务（opinion_mcp），对外暴露 6 个能力工具 |
| `renderer` | 3001 | Playwright 渲染服务，输出卡片 PNG |
| `xhs-mcp` | 18060 | 小红书 MCP 服务（Node.js），账号管理、认证、发布等 |

### MCP 工具（opinion_mcp）

- `render_cards` — 渲染可视化卡片（title/impact/radar/timeline/daily-rank/hot-topic）
- `publish_xhs_note` — 发布图文笔记到小红书
- `check_xhs_status` — 检查小红书登录状态
- `get_xhs_login_qrcode` — 生成登录二维码
- `check_xhs_login_session` — 检查扫码登录会话
- `submit_xhs_verification` — 提交短信验证码

### 工作流

分析和编排由宿主端 Skill 驱动（见 `.agents/skills/`），不再由云端 MCP 编排：

- **AI Daily**：`ai-insight` Skill → web search 采集 → 评分排名 → 渲染榜单卡片 → 发布
- **单话题深挖**：`ai-topic-analyzer` Skill → Discovery → Evidence → Crucible → Synthesis → Delivery

云端 MCP 仅在最终渲染卡片和发布小红书时被调用。

### 关键目录

- `opinion_mcp/` — MCP 服务与工具定义
- `renderer/` — 卡片渲染服务
- `.agents/skills/` — Skill 定义（ai-insight、ai-topic-analyzer）
- `cache/ai_daily/` — AI Daily 缓存
- `outputs/` — 卡片预览、分析输出等

## 快速开始

### Docker 部署（推荐）

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

#### 3. 启动 3 服务栈

```bash
docker compose up -d --build
```

#### 4. 验证服务

```bash
docker compose ps
docker compose logs --tail=60 mcp
curl http://localhost:18061/health
curl http://localhost:3001/healthz
```

#### 5. 停止服务

```bash
docker compose down
```

### 接入 MCP 客户端

MCP 服务暴露在：

- Health: `http://localhost:18061/health`
- MCP: `http://localhost:18061/mcp`

在 Claude Code / OpenCode 中添加：

- MCP 名称：`aiinsight-mcp`
- MCP URL：`http://localhost:18061/mcp`

说明：

- `18061` 是对外 MCP 服务地址
- `18060` 是内部 `xhs-mcp` sidecar，由 `mcp` 容器内部调用，不需要客户端直连

### 本地开发

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

4. 启动渲染器

```bash
cd renderer
npm run dev
```

5. 启动 MCP

```bash
python -m opinion_mcp.server --host 0.0.0.0 --port 18061
```

## 远程 Gateway 模式

当 AIInSight 部署为云端服务时，推荐用户只接入一个远程 MCP Gateway：

- `https://mcp.aiinsight.example.com/mcp`

此模式下：

- 用户侧只配置 **一个 MCP 地址 + 一个 API key**
- `mcp` / `renderer` / `xhs-mcp` 都位于云端私网
- 分析推理在宿主端 Skill 完成，仅渲染和发布调用远程 MCP

### 多账号隔离

远程 Gateway 模式下，每个 API key 对应一个独立 account：

- 独立 XHS 登录态
- 独立输出目录、二维码和卡片预览

MCP server 通过 API key 解析 account_id，不依赖客户端自报。

## 必要环境变量

至少需要配置一组可用 LLM Key（见上方快速开始）。

可选能力：

- `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USER_AGENT`
  - 启用 Reddit 社区证据
- `VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY`
  - 启用 AI 生图
- `XHS_MCP_URL`
  - 非 Docker Compose / 自定义部署时指定小红书 MCP 地址；默认 Docker Compose 自动使用 `http://xhs-mcp:18060/mcp`

### 小红书发布

`mcp` 容器通过容器网络访问 `http://xhs-mcp:18060/mcp`。

首次使用需登录：

1. 调用 MCP `get_xhs_login_qrcode` 获取二维码
2. 用小红书 App 扫码
3. 如需短信验证码，调用 `submit_xhs_verification`
4. 调用 `check_xhs_status` 确认登录成功

说明：

- `xhs-mcp` 作为 Docker sidecar 挂在默认 compose 中
- 数据持久化在 SQLite (`./runtime/xhs/data/data.db`)，容器重启不丢登录态
- 登录二维码和卡片预览保存在 `outputs/` 目录

Apple Silicon 说明：

- 通过 `Dockerfile.xhs-mcp` 自建镜像（Node.js 20 + Playwright Chromium），原生支持 ARM64

常见排障：

- 如果 `mcp` 容器反复退出，检查日志：`docker compose logs --tail=80 mcp`
- 如果端口被占，用 `docker ps` 找到旧容器并停止后重启

## 推荐使用方式

### AI Daily（日报）

通过 Skill 驱动，在 Claude Code / OpenCode 中：

1. 说"今日AI热点"或"AI日报" → 触发 `ai-insight` Skill
2. Skill 自动执行 web search 采集 → 评分排名 → 展示 Top 10
3. 选择话题深挖 → 自动委派给 `ai-topic-analyzer`
4. 渲染卡片 → 调用 `render_cards`
5. 发布到小红书 → 调用 `publish_xhs_note`

### 单话题深挖

1. 说"帮我分析 xxx" → 触发 `ai-topic-analyzer` Skill
2. 确认模式（quick/standard/deep）
3. Skill 自动完成 5 阶段分析
4. 按需渲染卡片和发布

## 当前约束

- 单话题深挖基于"近期 AI 来源语料 + 实时补全"，不是全网历史回溯搜索
- 单话题默认 source set 不包含 `producthunt_ai`
- `platform_radar` 卡片字段名仍被保留，但语义上已用于来源分布
