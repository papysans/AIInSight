# AIInSight

AI 内容生产工作台，提供两条主链路：

- **AI Daily**：聚合多源 AI 资讯，生成当日热点榜单并发布小红书
- **单话题深挖**：输入任意 AI 话题，5 阶段引擎自动完成分析、出图、发布

## 架构

**Skill-Driven 架构**：所有分析推理在宿主端 LLM（Skill）完成，云端只提供渲染和发布能力。

```
┌─────────────────────────────────┐
│  Claude Code / OpenCode         │
│                                 │
│  Skill: ai-insight              │  ← AI Daily 日报
│  Skill: ai-topic-analyzer       │  ← 单话题 5 阶段分析
└────────────┬────────────────────┘
             │ MCP（仅渲染/发布时调用）
┌────────────▼────────────────────┐
│  opinion_mcp  :18061            │
│  ├── render_cards               │  ← 渲染卡片 PNG
│  ├── publish_xhs_note           │  ← 发布小红书
│  ├── check_xhs_status           │
│  ├── get_xhs_login_qrcode       │
│  ├── check_xhs_login_session    │
│  └── submit_xhs_verification    │
└────────┬──────────┬─────────────┘
         │          │
  ┌──────▼──────┐  ┌▼─────────────────┐
  │  renderer   │  │    xhs-mcp       │
  │  :3001      │  │    :18060        │
  │ (Playwright)│  │ (Node.js + SQLite│
  └─────────────┘  └──────────────────┘
```

### 3 服务栈

| 服务 | 端口 | 说明 |
|------|------|------|
| `mcp` | 18061 | Python MCP Server，对外暴露 6 个工具 |
| `renderer` | 3001 | Playwright 卡片渲染服务 |
| `xhs-mcp` | 18060 | Node.js 小红书 MCP sidecar（容器内网） |

`xhs-mcp` 不对外暴露，只有 `mcp` 容器内部可访问。

---

## 安装与启动

### 前置要求

- Docker Engine 24+ 和 Docker Compose V2
- 至少一组 LLM API Key（Moonshot / DeepSeek / Doubao / Zhipu / Gemini）

### 第 1 步：克隆并配置环境变量

```bash
git clone https://github.com/papysans/AIInSight.git
cd AIInSight
cp .env.example .env
```

打开 `.env`，填入至少一组 LLM Key：

```env
# 任选其一（或多个）
MOONSHOT_API_KEYS=sk-xxx
DEEPSEEK_API_KEYS=sk-xxx
DOUBAO_API_KEYS=xxx
ZHIPU_API_KEYS=xxx
GEMINI_API_KEYS=xxx
```

其余配置保持默认即可。

### 第 2 步：启动服务

```bash
docker compose up -d --build
```

首次构建包含 Playwright Chromium，约需 3-5 分钟。

### 第 3 步：验证服务

```bash
docker compose ps
curl http://localhost:18061/health   # MCP Server
curl http://localhost:3001/healthz   # 渲染器
```

全部正常后进行下一步。

### 第 4 步：接入 Claude Code

在 Claude Code 中添加 MCP Server。

**方式 A — 直接使用项目配置（推荐）**

项目根目录已包含 `.mcp.json`，Claude Code 会自动读取：

```json
{
  "mcpServers": {
    "opinion-mcp": {
      "type": "url",
      "url": "http://localhost:18061/mcp"
    }
  }
}
```

**方式 B — 手动添加**

```bash
claude mcp add opinion-mcp --transport http http://localhost:18061/mcp
```

### 第 5 步：安装 Skill（可选，推荐）

将 `.agents/skills/` 下的两个 Skill 复制到你的 Claude Code 全局 skills 目录，以启用 `ai-insight` 和 `ai-topic-analyzer` 的完整工作流：

```bash
# Claude Code
cp -r .agents/skills/ai-insight ~/.claude/skills/
cp -r .agents/skills/ai-topic-analyzer ~/.claude/skills/
cp -r .agents/skills/shared ~/.claude/skills/
```

或手动按宿主端格式安装（OpenCode / Roo 等配置已在 `.opencode/` 和 `.roo/` 目录中）。

---

## 使用方法

### AI Daily（日报）

在 Claude Code 中说：

```
今日AI热点
```

Skill 自动执行：Web 搜索采集 → 评分排名 → 展示 Top 10 → 用户选题 → 委派深挖 → 渲染卡片 → 发布小红书。

### 单话题深挖

```
帮我分析 GPT-5
```

5 阶段流程：
1. **Discovery** — 多维 Web 搜索（Technical / Market / Sentiment）
2. **Evidence** — 结构化证据表（High / Medium / Low 可信度）
3. **Deep Search** — 垂直数据源定向检索（AIBase、机器之心、量子位、TechCrunch、arXiv、GitHub）
4. **Smart Synthesis** — 单轮 LLM 分析，输出置信度评分
5. **Delivery** — 渲染 4 张卡片 → 发布小红书

分析模式：

| 模式 | Deep Search | Discovery | 适用场景 |
|------|-------------|-----------|---------|
| `quick` | 跳过 | 3 次 | 快速概览 |
| `standard`（默认） | 3-5 次 | 6 次 | 标准深挖 |
| `deep` | 6-9 次 | 9 次 | 全量研究 |

---

## 小红书登录

首次发布前需要登录。在 Claude Code 中直接说：

```
登录小红书
```

Skill 会自动调用 `get_xhs_login_qrcode` → 展示二维码 → 等待扫码 → 处理短信验证码（如需）。

登录态持久化在 `./runtime/xhs/data/data.db`，容器重启不丢失。

---

## 云端部署

将 MCP 服务部署到云端，供多台设备远程使用。详见 [CLOUD_DEPLOYMENT_GUIDE.md](docs/CLOUD_DEPLOYMENT_GUIDE.md)。

简要流程：

```bash
# 1. 配置域名和 API Key 认证
echo "OPINION_REQUIRE_API_KEY=true" >> .env
echo "OPINION_ADMIN_TOKEN=your-secret" >> .env
echo "OPINION_DOMAIN=mcp.example.com" >> .env

# 2. 启动（含 Caddy HTTPS 反代）
docker compose -f docker-compose.cloud.yml up -d --build

# 3. 创建 API Key
curl -X POST https://mcp.example.com/admin/api-keys \
  -H "Authorization: Bearer your-secret" \
  -d '{"label": "my-key"}'
```

客户端 `.mcp.json`：

```json
{
  "mcpServers": {
    "opinion-mcp": {
      "type": "url",
      "url": "https://mcp.example.com/mcp",
      "headers": { "X-API-Key": "your-api-key" }
    }
  }
}
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `MOONSHOT_API_KEYS` | Moonshot API Key（逗号分隔支持多 Key） | — |
| `DEEPSEEK_API_KEYS` | DeepSeek API Key | — |
| `DOUBAO_API_KEYS` | 豆包 API Key | — |
| `ZHIPU_API_KEYS` | 智谱 API Key | — |
| `GEMINI_API_KEYS` | Gemini API Key | — |
| `VOLC_ACCESS_KEY` / `VOLC_SECRET_KEY` | 火山引擎（AI 生图，可选） | — |
| `XHS_MCP_REQUEST_INTERVAL` | 小红书请求间隔（ms） | `2000` |
| `OPINION_REQUIRE_API_KEY` | 开启 API Key 认证（云端用） | `false` |
| `OPINION_ADMIN_TOKEN` | Admin API 令牌（云端用） | — |
| `OPINION_DOMAIN` | 域名（Caddy HTTPS，云端用） | — |

---

## 目录结构

```
.
├── opinion_mcp/          # MCP Server（Python）
│   ├── server.py         # 入口
│   ├── tools/            # MCP 工具定义
│   └── services/         # 渲染、发布、XHS 适配层
├── renderer/             # 卡片渲染服务（Node.js + Playwright）
├── .agents/skills/       # Skill 定义（宿主端分析引擎）
│   ├── ai-insight/       # AI Daily 日报 Skill
│   ├── ai-topic-analyzer/ # 单话题深挖 Skill
│   └── shared/           # 共享 Guidelines
├── .opencode/skills/     # OpenCode 同步副本
├── .roo/skills/          # Roo 同步副本
├── outputs/              # 卡片预览输出
├── runtime/xhs/          # XHS 登录数据（SQLite）
├── .mcp.json             # Claude Code MCP 配置
└── docker-compose.yml    # 3 服务栈编排
```

---

## 排障

**服务启动失败**

```bash
docker compose logs --tail=80 mcp
docker compose logs --tail=80 xhs-mcp
```

**渲染器无响应**

```bash
curl http://localhost:3001/healthz
docker compose restart renderer
```

**小红书登录态丢失**

```bash
# 检查 SQLite 是否正常挂载
docker compose exec xhs-mcp ls /data
```

**Apple Silicon（M 系列芯片）**

`xhs-mcp` 镜像基于 `Dockerfile.xhs-mcp` 自建，原生支持 ARM64，无需额外处理。
