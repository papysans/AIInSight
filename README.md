# AIInSight

AI 内容生产工作台，提供两条主链路：

- **AI Daily**：聚合多源 AI 资讯，生成当日热点榜单并发布小红书
- **单话题深挖**：输入任意 AI 话题，5 阶段引擎自动完成分析、出图、发布

## 架构

**Skill-Driven 架构**：所有分析推理在宿主端 LLM（Skill）完成，云端只提供渲染和发布能力。

```
┌─────────────────────────────────┐
│  Costrict / Claude Code / Opencode  │
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

AIInSight 支持两种部署模式：**本地部署**（MCP 跑在本机）和**云端部署**（MCP 跑在远程服务器，多设备共享）。

### 前置要求

- Docker Engine 24+ 和 Docker Compose V2
- 任意一个支持 MCP 的 AI Coding 平台（Costrict / Claude Code / Opencode）

---

### 方式 A：本地部署

适合单设备使用，服务跑在本机。

#### 1. 克隆并配置

```bash
git clone https://github.com/papysans/AIInSight.git
cd AIInSight
cp .env.example .env
```

`.env` 默认配置即可直接使用，无需填写 LLM Key（所有推理在宿主端完成）。

#### 2. 启动服务

```bash
docker compose up -d --build
```

首次构建包含 Playwright Chromium，约需 3-5 分钟。

#### 3. 验证服务

```bash
docker compose ps
curl http://localhost:18061/health   # MCP Server
curl http://localhost:3001/healthz   # 渲染器
```

#### 4. 接入 MCP

项目根目录已包含各平台的 MCP 配置文件，克隆后自动生效：

| 平台 | 配置文件 | 说明 |
|------|---------|------|
| Costrict / Opencode | `opencode.json` | 自动读取 |
| Claude Code | `.mcp.json` | 自动读取 |

如需手动配置，见下方 [MCP 配置参考](#mcp-配置参考)。

---

### 方式 B：云端部署（推荐）

将 MCP 服务部署到云服务器，多台设备远程共享，无需每台机器跑 Docker。

#### 1. 服务器准备

在云服务器上安装 Docker（以 Debian/Ubuntu 为例）：

```bash
# 国内服务器使用阿里云镜像源
apt-get update && apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.aliyun.com/docker-ce/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list
apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

配置 Docker 镜像加速和 DNS（国内服务器必需）：

```bash
cat > /etc/docker/daemon.json << 'EOF'
{
  "registry-mirrors": ["https://mirror.ccs.tencentyun.com"],
  "dns": ["223.5.5.5", "8.8.8.8"]
}
EOF
systemctl restart docker
```

#### 2. 上传项目并配置

```bash
# 从本地同步项目到服务器
rsync -avz --exclude '.venv' --exclude '.git' --exclude '__pycache__' \
  --exclude 'node_modules' --exclude '.env' \
  ./  root@YOUR_SERVER_IP:/opt/aiinsight/
```

在服务器上创建 `.env`：

```bash
cat > /opt/aiinsight/.env << 'EOF'
PUBLIC_API_BASE_URL=http://YOUR_SERVER_IP:18061
OPINION_REQUIRE_API_KEY=true
OPINION_ADMIN_TOKEN=your-admin-token-here
TZ=Asia/Shanghai
XHS_MCP_SOURCE_TIMEZONE=Asia/Shanghai
EOF
```

> **国内服务器注意**：容器内 apt 源需改为国内镜像，否则构建会超时。
> 在各 Dockerfile 的 `FROM` 之后、`RUN apt-get` 之前加入：
> ```dockerfile
> RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null; true
> ```

#### 3. 构建并启动

```bash
cd /opt/aiinsight
mkdir -p cache outputs runtime/xhs/data/logs runtime/xhs/images
docker compose up -d --build
```

#### 4. 创建 API Key

```bash
# 用 ADMIN_TOKEN 创建一个 API Key
curl -X POST http://localhost:18061/admin/api-keys \
  -H "Authorization: Bearer your-admin-token-here" \
  -H "Content-Type: application/json" \
  -d '{"account_id": "my-account", "note": "my device"}'
```

返回的 `api_key` 字段即为客户端使用的密钥。

#### 5. 验证

```bash
curl http://YOUR_SERVER_IP:18061/health
```

> **安全组提醒**：阿里云/腾讯云等需要在安全组中放行 18061 端口（TCP）。

---

### 接入 MCP（客户端配置）

<a id="mcp-配置参考"></a>

无论本地还是云端，客户端只需配置 MCP 地址即可。Skill 通过 MCP 配置自动发现服务，不硬编码地址。

**Claude Code（`.mcp.json`）：**

```json
{
  "mcpServers": {
    "opinion-mcp": {
      "type": "url",
      "url": "http://YOUR_SERVER_IP:18061/mcp",
      "headers": { "X-API-Key": "your-api-key" }
    }
  }
}
```

> 本地部署时 URL 为 `http://localhost:18061/mcp`，可省略 headers。

**Costrict / Opencode（`opencode.json`）：**

```json
{
  "mcp": {
    "aiinsight-mcp": {
      "type": "remote",
      "url": "http://YOUR_SERVER_IP:18061/mcp",
      "headers": { "X-API-Key": "your-api-key" }
    }
  }
}
```

**手动添加（Claude Code CLI）：**

```bash
claude mcp add opinion-mcp --transport http http://YOUR_SERVER_IP:18061/mcp
```

---

### 安装 Skill

Skill 是运行在你本地 AI Coding 平台上的工作流定义，所有分析推理在本地 LLM 完成，仅渲染和发布时调用云端 MCP。

用户只需完成以下 3 步即可使用：

#### Step 1：配置 MCP 连接

见上方 [接入 MCP（客户端配置）](#mcp-配置参考)，将 MCP 地址指向云端服务器。

#### Step 2：安装 Skill 文件

从 GitHub 直接下载，无需克隆整个项目：

**Claude Code：**

```bash
mkdir -p ~/.claude/skills/{ai-insight,ai-topic-analyzer,shared}
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.agents/skills/ai-insight/SKILL.md -o ~/.claude/skills/ai-insight/SKILL.md
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.agents/skills/ai-topic-analyzer/SKILL.md -o ~/.claude/skills/ai-topic-analyzer/SKILL.md
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.agents/skills/shared/GUIDELINES.md -o ~/.claude/skills/shared/GUIDELINES.md
```

**Costrict CLI / VSCode Costrict 插件：**

```bash
mkdir -p ~/.costrict/skills/{ai-insight,ai-topic-analyzer,shared}
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-insight/SKILL.md -o ~/.costrict/skills/ai-insight/SKILL.md
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-topic-analyzer/SKILL.md -o ~/.costrict/skills/ai-topic-analyzer/SKILL.md
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/shared/GUIDELINES.md -o ~/.costrict/skills/shared/GUIDELINES.md
```

**Opencode：**

```bash
mkdir -p ~/.opencode/skills/{ai-insight,ai-topic-analyzer,shared}
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-insight/SKILL.md -o ~/.opencode/skills/ai-insight/SKILL.md
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-topic-analyzer/SKILL.md -o ~/.opencode/skills/ai-topic-analyzer/SKILL.md
curl -sL https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/shared/GUIDELINES.md -o ~/.opencode/skills/shared/GUIDELINES.md
```

| 平台 | 全局 Skill 路径 |
|------|----------------|
| Claude Code | `~/.claude/skills/` |
| Costrict CLI / VSCode 插件 | `~/.costrict/skills/` |
| Opencode | `~/.opencode/skills/` |

#### Step 3：确认 Web Search 可用

Skill 依赖平台的 **web search** 能力进行新闻采集和证据收集。各平台情况：

| 平台 | Web Search | 说明 |
|------|-----------|------|
| Claude Code | 内置 `WebSearch` 工具 | 开箱即用，无需配置 |
| Opencode / Costrict | 需配置 search MCP | 推荐 `exa-search` 或类似 MCP server |

> Skill 启动时会自动检查 `web_search` 和 `mcp_gateway` 两项依赖。MCP 连接失败只影响渲染/发布功能，分析流程仍可正常运行。

---

## 使用方法

### AI Daily（日报）

在你的 AI Coding 平台中说：

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

首次发布前需要登录。在你的 AI Coding 平台中直接说：

```
登录小红书
```

Skill 会自动调用 `get_xhs_login_qrcode` → 展示二维码 → 等待扫码 → 处理短信验证码（如需）。

登录态持久化在 `./runtime/xhs/data/data.db`，容器重启不丢失。

---

## 云端部署（进阶）

如需使用域名 + HTTPS（Caddy 自动证书），详见 [CLOUD_DEPLOYMENT_GUIDE.md](docs/CLOUD_DEPLOYMENT_GUIDE.md)。

```bash
# 配置域名
echo "OPINION_DOMAIN=mcp.example.com" >> .env

# 启动（含 Caddy HTTPS 反代）
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build
```

> 无域名时使用 IP + 端口直连即可（见上方 [方式 B](#方式-b云端部署推荐)），无需 Caddy。

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
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
├── .agents/skills/       # Skill 定义（Claude Code 格式）
│   ├── ai-insight/       # AI Daily 日报 Skill
│   ├── ai-topic-analyzer/ # 单话题深挖 Skill
│   └── shared/           # 共享 Guidelines
├── .opencode/skills/     # Opencode / Costrict 格式 Skill
├── .roo/skills/          # Roo 同步副本
├── .mcp.json             # Claude Code MCP 配置
├── opencode.json         # Opencode / Costrict MCP 配置
├── outputs/              # 卡片预览输出
├── runtime/xhs/          # XHS 登录数据（SQLite）
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
