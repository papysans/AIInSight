# AIInSight

<div align="center">

<p><strong>AI 内容生产工作台 — 从热点采集到小红书发布，一句话搞定</strong></p>

<p>
  <a href="#quick-start">Quick Start</a> ·
  <a href="#features">Features</a> ·
  <a href="#platforms">Platforms</a> ·
  <a href="#for-agents">For Agents</a> ·
  <a href="#self-hosting">Self-Hosting</a>
</p>

</div>

## Why AIInSight?

AI 资讯每天爆炸式增长，手动追踪、整理、出图、发布是重复劳动。

AIInSight 把这些全自动化：**一句话触发 → AI 自动搜索采集 → 分析评分 → 渲染卡片 → 发布小红书**。所有推理在你本地 LLM 完成，云端只负责渲染和发布。

两条主链路：

- **AI Daily**：聚合多源 AI 资讯，生成当日热点榜单并发布小红书
- **单话题深挖**：输入任意 AI 话题，5 阶段引擎自动完成分析、出图、发布

## Quick Start

两步完成配置，无需克隆整个项目：

**第 1 步：安装 Skill（一键自动检测平台）**

```bash
curl -fsSL https://raw.githubusercontent.com/papysans/AIInSight/main/install.sh | bash
```

如果自动检测失败，手动指定平台：

```bash
curl -fsSL https://raw.githubusercontent.com/papysans/AIInSight/main/install.sh | bash -s -- --platform <platform>
```

可选：`claude-code`、`opencode`、`costrict`、`vscode-costrict`

**第 2 步：配置 MCP 连接**

将 MCP 地址写入你平台的全局配置文件（见 [Platforms](#platforms) 获取各平台路径）。

安装完成后试试：

```
今日AI热点
```

或者复制以下 prompt 丢给你的 AI Agent：

```
你是一个自动化安装助手。请访问以下 URL 并阅读其中的 "For Agents" 部分，
严格按照步骤完成 AIInSight Skill 的安装。

不要 clone 整个仓库，只需要读取这个 raw URL 的内容：
https://raw.githubusercontent.com/papysans/AIInSight/main/README.md

根据你所在的平台（Claude Code / Opencode / Costrict CLI / VSCode Costrict），
执行对应的安装命令。安装完成后告诉我结果。
```

---

## Features

| 功能 | 说明 |
|------|------|
| AI Daily 日报 | Web 搜索采集 → 评分排名 → Top 10 → 用户选题 → 深挖 → 渲染卡片 → 发布 |
| 单话题深挖 | 5 阶段流程：Discovery → Evidence → Deep Search → Smart Synthesis → Delivery |
| 卡片渲染 | verdict / evidence / delta / action 四张卡片，Playwright 生成 PNG |
| 小红书发布 | 自动登录（扫码）、自动发布、登录态持久化 |
| 多平台支持 | Claude Code / Opencode / Costrict CLI / VSCode Costrict |

### 单话题分析模式

| 模式 | Deep Search | Discovery | 适用场景 |
|------|-------------|-----------|---------|
| `quick` | 跳过 | 3 次 | 快速概览 |
| `standard`（默认） | 3-5 次 | 6 次 | 标准深挖 |
| `deep` | 6-9 次 | 9 次 | 全量研究 |

---

## Platforms

支持四个 AI Coding 平台，Skill 内容一致，安装路径不同：

| | Claude Code | Opencode | Costrict CLI | VSCode Costrict (Roo Code) |
|---|---|---|---|---|
| Skill 路径 | `~/.claude/skills/` | `~/.opencode/skills/` | `~/.costrict/skills/` | `~/.roo/skills/` |
| MCP 配置 | `~/.claude/.mcp.json` | 项目 `opencode.json` | `~/.costrict/settings.json` | `~/.roo/mcp.json` |
| Web Search | 内置 `WebSearch` | 需配置 search MCP | 需配置 search MCP | 需配置 search MCP |

<details>
<summary>MCP 配置示例</summary>

**Claude Code（`~/.claude/.mcp.json`）：**

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

**Costrict CLI（`~/.costrict/settings.json`）：**

```json
{
  "mcpServers": {
    "opinion-mcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://YOUR_SERVER_IP:18061/mcp"],
      "env": { "API_KEY": "your-api-key" }
    }
  }
}
```

> Costrict CLI 基于 Gemini CLI，MCP 配置在 `settings.json` 的 `mcpServers` 字段中。

**VSCode Costrict / Roo Code（`~/.roo/mcp.json`）：**

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

**Opencode（项目 `opencode.json`）：**

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

</details>

<details>
<summary>平台环境变量自动检测</summary>

`install.sh` 通过以下进程级环境变量自动识别平台：

| 环境变量 | 平台 |
|---------|------|
| `COSTRICT_CALLER=vscode` | VSCode Costrict |
| `COSTRICT_RUNNING=1` | Costrict CLI |
| `CLAUDECODE=1` | Claude Code |
| `OPENCODE=1` | Opencode |

</details>

---

## For Agents

> **AI Agent 请阅读本节完成自动安装。** 请严格按照以下步骤执行，不要跳过任何一步。

### 第 1 步：安装 Skill

执行以下命令，脚本会自动检测当前平台并安装到正确路径：

```bash
curl -fsSL https://raw.githubusercontent.com/papysans/AIInSight/main/install.sh | bash
```

如果自动检测失败，手动指定平台：

```bash
curl -fsSL https://raw.githubusercontent.com/papysans/AIInSight/main/install.sh | bash -s -- --platform <platform>
```

可选：`claude-code`、`opencode`、`costrict`、`vscode-costrict`

<details>
<summary>如果无法执行 curl | bash（备选方案）</summary>

根据你的平台，手动执行对应命令：

**Claude Code：**

```bash
mkdir -p ~/.claude/skills/{ai-insight,ai-topic-analyzer,shared}
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.agents/skills/ai-insight/SKILL.md" -o ~/.claude/skills/ai-insight/SKILL.md
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.agents/skills/ai-topic-analyzer/SKILL.md" -o ~/.claude/skills/ai-topic-analyzer/SKILL.md
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.agents/skills/shared/GUIDELINES.md" -o ~/.claude/skills/shared/GUIDELINES.md
```

**Opencode：**

```bash
mkdir -p ~/.opencode/skills/{ai-insight,ai-topic-analyzer,shared}
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-insight/SKILL.md" -o ~/.opencode/skills/ai-insight/SKILL.md
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-topic-analyzer/SKILL.md" -o ~/.opencode/skills/ai-topic-analyzer/SKILL.md
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/shared/GUIDELINES.md" -o ~/.opencode/skills/shared/GUIDELINES.md
```

**Costrict CLI / VSCode Costrict（Roo Code）：**

```bash
# Costrict CLI
mkdir -p ~/.costrict/skills/{ai-insight,ai-topic-analyzer,shared}
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-insight/SKILL.md" -o ~/.costrict/skills/ai-insight/SKILL.md
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-topic-analyzer/SKILL.md" -o ~/.costrict/skills/ai-topic-analyzer/SKILL.md
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/shared/GUIDELINES.md" -o ~/.costrict/skills/shared/GUIDELINES.md

# VSCode Costrict (Roo Code)
mkdir -p ~/.roo/skills/{ai-insight,ai-topic-analyzer,shared}
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-insight/SKILL.md" -o ~/.roo/skills/ai-insight/SKILL.md
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/ai-topic-analyzer/SKILL.md" -o ~/.roo/skills/ai-topic-analyzer/SKILL.md
curl -fsSL "https://raw.githubusercontent.com/papysans/AIInSight/main/.opencode/skills/shared/GUIDELINES.md" -o ~/.roo/skills/shared/GUIDELINES.md
```

</details>

### 第 2 步：配置 MCP 连接

根据当前平台，将 MCP 配置写入对应配置文件。用户需要提供 MCP 服务器地址和 API Key。

**Claude Code** → 写入 `~/.claude/.mcp.json`：
```json
{
  "mcpServers": {
    "opinion-mcp": {
      "type": "url",
      "url": "http://MCP_SERVER_ADDRESS:18061/mcp",
      "headers": { "X-API-Key": "USER_API_KEY" }
    }
  }
}
```

**VSCode Costrict / Roo Code** → 写入 `~/.roo/mcp.json`：
```json
{
  "mcpServers": {
    "opinion-mcp": {
      "type": "url",
      "url": "http://MCP_SERVER_ADDRESS:18061/mcp",
      "headers": { "X-API-Key": "USER_API_KEY" }
    }
  }
}
```

**Opencode** → 写入项目根目录 `opencode.json`：
```json
{
  "mcp": {
    "aiinsight-mcp": {
      "type": "remote",
      "url": "http://MCP_SERVER_ADDRESS:18061/mcp",
      "headers": { "X-API-Key": "USER_API_KEY" }
    }
  }
}
```

**Costrict CLI** → 写入 `~/.costrict/settings.json`（添加 `mcpServers` 字段）：
```json
{
  "mcpServers": {
    "opinion-mcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://MCP_SERVER_ADDRESS:18061/mcp"],
      "env": { "API_KEY": "USER_API_KEY" }
    }
  }
}
```

> 如果用户提供了具体的 IP 和 API Key，直接替换上面的占位符。本地部署时 URL 为 `http://localhost:18061/mcp`，可省略 headers。

### 第 3 步：验证

安装完成后，告诉用户说「今日AI热点」或「帮我分析 GPT-5」来验证 Skill 是否正常工作。

---

## Self-Hosting

AIInSight 的云端服务（MCP + 渲染器 + 小红书）可以自行部署。

### 架构

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

| 服务 | 端口 | 说明 |
|------|------|------|
| `mcp` | 18061 | Python MCP Server，对外暴露 6 个工具 |
| `renderer` | 3001 | Playwright 卡片渲染服务 |
| `xhs-mcp` | 18060 | Node.js 小红书 MCP sidecar（容器内网，不对外暴露） |

### 方式 A：本地部署

适合单设备使用，服务跑在本机。

```bash
git clone https://github.com/papysans/AIInSight.git
cd AIInSight
cp .env.example .env
docker compose up -d --build
```

首次构建包含 Playwright Chromium，约需 3-5 分钟。验证：

```bash
curl http://localhost:18061/health   # MCP Server
curl http://localhost:3001/healthz   # 渲染器
```

项目根目录已包含各平台 MCP 配置（`.mcp.json`、`opencode.json`），克隆后自动生效。

### 方式 B：云端部署（推荐）

将服务部署到云服务器，多台设备远程共享。

#### 1. 服务器准备

安装 Docker（以 Debian/Ubuntu 为例，国内服务器用阿里云镜像源）：

```bash
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

### HTTPS（进阶）

如需使用域名 + HTTPS（Caddy 自动证书），详见 [CLOUD_DEPLOYMENT_GUIDE.md](docs/CLOUD_DEPLOYMENT_GUIDE.md)。

```bash
echo "OPINION_DOMAIN=mcp.example.com" >> .env
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build
```

---

## 小红书登录（不稳定，谨慎使用）

首次发布前需要登录。在你的 AI Coding 平台中直接说：

```
登录小红书
```

Skill 会自动调用 `get_xhs_login_qrcode` → 展示二维码 → 等待扫码 → 处理短信验证码（如需）。

登录态持久化在 `./runtime/xhs/data/data.db`，容器重启不丢失。

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `XHS_MCP_REQUEST_INTERVAL` | 小红书请求间隔（ms） | `2000` |
| `OPINION_REQUIRE_API_KEY` | 开启 API Key 认证（云端用） | `false` |
| `OPINION_ADMIN_TOKEN` | Admin API 令牌（云端用） | — |
| `OPINION_DOMAIN` | 域名（Caddy HTTPS，云端用） | — |

> 无需配置 LLM API Key，所有推理在宿主端 LLM 完成。

---

<details>
<summary>目录结构</summary>

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
├── .roo/                 # VSCode Costrict 格式
├── install.sh            # 一键安装脚本（自动检测平台）
├── .mcp.json             # Claude Code MCP 配置（本地开发用）
├── opencode.json         # Opencode / Costrict MCP 配置（本地开发用）
├── outputs/              # 卡片预览输出
├── runtime/xhs/          # XHS 登录数据（SQLite）
└── docker-compose.yml    # 3 服务栈编排
```

</details>

<details>
<summary>排障</summary>

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
docker compose exec xhs-mcp ls /data
```

**Apple Silicon（M 系列芯片）**

`xhs-mcp` 镜像基于 `Dockerfile.xhs-mcp` 自建，原生支持 ARM64，无需额外处理。

</details>
