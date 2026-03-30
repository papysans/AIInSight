# AIInSight 云端部署指南

> 将 AIInSight MCP Server 部署到云端，通过域名 + HTTPS + API Key 为远程客户端提供服务。

---

## 目录

1. [架构概览](#架构概览)
2. [前置条件](#前置条件)
3. [快速部署](#快速部署)
4. [创建 API Key](#创建-api-key)
5. [客户端配置](#客户端配置)
6. [安全加固](#安全加固)
7. [环境变量参考](#环境变量参考)
8. [排障](#排障)

---

## 架构概览

### 本地 vs 云端

```
本地模式：
  Claude Code → localhost:18061/mcp → MCP Server → renderer / xhs-mcp

云端模式：
  Claude Code → https://mcp.example.com/mcp (X-API-Key) → Caddy (HTTPS) → MCP Server → renderer / xhs-mcp
```

### 云端架构图

```
┌──────────────────────────────────────────────────────────────┐
│  Cloud Server                                                │
│                                                              │
│  ┌────────────┐                                              │
│  │   Caddy    │ :443 (HTTPS, 自动证书)                        │
│  │  反向代理   │                                              │
│  └─────┬──────┘                                              │
│        │                                                     │
│  ┌─────▼──────┐     ┌───────────┐     ┌──────────────────┐  │
│  │    mcp     │────→│ renderer  │     │     xhs-mcp      │  │
│  │   :18061   │────→│  :3001    │     │     :18060       │  │
│  │ (API Key)  │     │(Playwright)│     │(Playwright+SQLite)│  │
│  └────────────┘     └───────────┘     └──────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
         ▲
         │ HTTPS + X-API-Key
┌────────┴─────────┐
│  Claude Code     │
│  (本地客户端)     │
│  .mcp.json       │
└──────────────────┘
```

关键特征：
- **Caddy** 自动申请 Let's Encrypt 证书，零配置 HTTPS
- **renderer** 和 **xhs-mcp** 不对外暴露端口，仅 Docker 内网可达
- 所有 MCP 请求必须携带 `X-API-Key`，由 MCP Server 校验并映射到账户

---

## 前置条件

| 要求 | 说明 |
|------|------|
| 服务器 | Linux 2C4G+（renderer 的 Playwright 需要内存） |
| Docker | Docker Engine 24+ 和 Docker Compose V2 |
| 域名 | 已指向服务器 IP 的域名（Caddy 需要做域名验证） |
| 端口 | 开放 80 和 443（Caddy HTTPS） |

---

## 快速部署

### 1. 克隆代码

```bash
git clone https://github.com/your-org/AIInSight.git
cd AIInSight
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，填入必需的配置：

```env
# 云端部署必填
OPINION_REQUIRE_API_KEY=true
OPINION_ADMIN_TOKEN=your-secret-admin-token
OPINION_DOMAIN=mcp.example.com
```

> **OPINION_ADMIN_TOKEN** 用于保护 Admin API，请使用强随机字符串：
> ```bash
> python3 -c "import secrets; print(secrets.token_urlsafe(32))"
> ```

### 3. 启动服务

```bash
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build
```

这会启动 4 个容器：

| 服务 | 说明 | 对外端口 |
|------|------|---------|
| caddy | HTTPS 反向代理 | 80, 443 |
| mcp | MCP Server | 仅内网 |
| renderer | 卡片渲染 | 仅内网 |
| xhs-mcp | 小红书运行时 | 仅内网 |

### 4. 验证部署

```bash
# 健康检查（通过 Caddy HTTPS）
curl https://mcp.example.com/health

# 预期返回
{
  "status": "healthy",
  "service": "AIInSight MCP Server",
  "version": "2.0.0",
  "available_tools": ["render_cards", "publish_xhs_note", ...]
}
```

---

## 创建 API Key

部署完成后，使用 Admin Token 创建 API Key：

```bash
# 创建 Key
curl -X POST https://mcp.example.com/admin/api-keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-admin-token" \
  -d '{"account_id": "user-1", "note": "Claude Code 主力"}'
```

返回：

```json
{
  "api_key": "aBcDeFgHiJkLmNoPqRsTuVwXyZ012345",
  "account_id": "user-1",
  "note": "Claude Code 主力",
  "status": "active",
  "created_at": "2026-03-25T12:00:00Z"
}
```

其他管理操作：

```bash
# 列出所有 Key
curl https://mcp.example.com/admin/api-keys \
  -H "X-Admin-Token: your-secret-admin-token"

# 吊销 Key
curl -X POST https://mcp.example.com/admin/api-keys/revoke \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-secret-admin-token" \
  -d '{"api_key": "aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"}'
```

---

## 客户端配置

### Claude Code

在项目根目录创建或修改 `.mcp.json`：

```json
{
  "mcpServers": {
    "opinion-mcp": {
      "type": "url",
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "X-API-Key": "aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"
      }
    }
  }
}
```

重启 Claude Code 会话后，6 个 MCP 工具自动可用：
- `render_cards` — 渲染卡片
- `publish_xhs_note` — 发布小红书
- `check_xhs_status` — 检查登录状态
- `get_xhs_login_qrcode` — 获取登录二维码
- `check_xhs_login_session` — 轮询扫码状态
- `submit_xhs_verification` — 提交短信验证码

### OpenCode / 其他 MCP Client

任何支持 StreamableHTTP 传输的 MCP Client 都可以连接。关键参数：

- **URL**: `https://mcp.example.com/mcp`
- **传输协议**: StreamableHTTP（POST JSON-RPC → SSE 响应）
- **认证 Header**: `X-API-Key: <your-key>` 或 `Authorization: Bearer <your-key>`

### 本地开发切换

如果需要切回本地 Docker 开发，将 `.mcp.json` 改回：

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

本地模式不需要 API Key（`OPINION_REQUIRE_API_KEY` 默认 `false`）。

> 提示：项目中提供了 `.mcp.cloud.json.example` 作为云端配置模板参考。

---

## 安全加固

### 防火墙

只开放 Caddy 所需的端口：

```bash
# UFW 示例
ufw allow 80/tcp    # Caddy HTTP → HTTPS 重定向
ufw allow 443/tcp   # Caddy HTTPS
ufw allow 22/tcp    # SSH
ufw deny 18061      # MCP 不直接暴露
ufw deny 3001       # renderer 不暴露
ufw deny 18060      # xhs-mcp 不暴露
ufw enable
```

### Admin Token

- 云端模式下 Admin API 必须配置 `OPINION_ADMIN_TOKEN`
- 不配置时，`REQUIRE_API_KEY=true` 模式下 Admin API 会返回 403
- Admin Token 与 API Key 是独立的：API Key 用于普通 MCP 调用，Admin Token 仅用于管理 API Key

### CORS

MCP Server 默认允许所有来源（`allow_origins=["*"]`）。如果需要限制：

```python
# opinion_mcp/server.py 中修改
allow_origins=["https://mcp.example.com"]
```

### 速率限制（推荐）

当前未内置速率限制。可通过 Caddy 插件或云服务商的 WAF/API Gateway 实现。

---

## 环境变量参考

### 核心配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPINION_REQUIRE_API_KEY` | `false` | 是否强制 MCP 请求携带 API Key |
| `OPINION_ADMIN_TOKEN` | (空) | Admin API 访问令牌 |
| `OPINION_DOMAIN` | `localhost` | 域名（Caddy 证书申请用） |

### 服务配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RENDERER_SERVICE_URL` | `http://renderer:3001` | 渲染器地址（Docker 内网） |
| `XHS_MCP_URL` | `http://xhs-mcp:18060/mcp` | XHS MCP 地址（Docker 内网） |
| `OPINION_MCP_PORT` | `18061` | MCP Server 端口 |
| `OPINION_API_KEY_REGISTRY_PATH` | `cache/api_keys.json` | API Key 存储路径 |
| `OPINION_REQUEST_TIMEOUT` | `300` | 请求超时（秒） |

### XHS 运行时

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `XHS_MCP_HEADLESS` | `true` | 无头浏览器模式 |
| `XHS_MCP_PORT` | `18060` | XHS MCP 端口 |
| `XHS_MCP_REQUEST_INTERVAL` | `2000` | 请求间隔（毫秒） |
| `XHS_MCP_LOG_LEVEL` | `info` | 日志级别 |
| `XHS_LOGIN_QRCODE_TIMEOUT_SECONDS` | `60` | 二维码超时 |

---

## 排障

### 服务状态检查

```bash
# 查看所有容器
docker compose -f docker-compose.yml -f docker-compose.cloud.yml ps

# 查看 MCP 日志
docker compose logs --tail=50 mcp

# 查看 Caddy 日志
docker compose logs --tail=50 caddy

# 查看渲染器日志
docker compose logs --tail=50 renderer
```

### 常见问题

#### Q: Caddy 证书申请失败

1. 确认域名 DNS 已指向服务器 IP
2. 确认 80 和 443 端口已开放
3. 查看 Caddy 日志：`docker compose logs caddy`

#### Q: MCP 请求返回 401

```json
{"detail": "Missing or invalid API key"}
```

- 确认 `.mcp.json` 中的 `X-API-Key` 值正确
- 确认 Key 状态为 `active`（用 Admin API 查看）

#### Q: Admin API 返回 403

```json
{"detail": "Invalid admin token"}
```

- 确认 `OPINION_ADMIN_TOKEN` 环境变量已配置
- 确认请求头 `X-Admin-Token` 值与环境变量一致

#### Q: 渲染超时

- renderer 容器需要足够内存（建议 2G+）
- 首次渲染需要 Playwright 加载 Chromium，可能较慢
- 检查 renderer 日志：`docker compose logs renderer`

#### Q: 本地开发如何跳过 API Key

本地 `docker compose up -d`（不加 cloud overlay）即可，`OPINION_REQUIRE_API_KEY` 默认 `false`。

---

## 更新与维护

### 更新部署

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.cloud.yml up -d --build
```

### 备份

需要持久化的数据：

| 路径 | 内容 |
|------|------|
| `cache/api_keys.json` | API Key 注册表 |
| `runtime/xhs/data/` | XHS 登录状态（SQLite） |
| `caddy_data` volume | HTTPS 证书 |

### 重置 XHS 登录

如果小红书登录过期，通过 MCP 工具重新扫码：

1. 调用 `get_xhs_login_qrcode` 获取二维码
2. 用小红书 App 扫码
3. 调用 `check_xhs_login_session` 确认状态
4. 如需短信验证，调用 `submit_xhs_verification`
