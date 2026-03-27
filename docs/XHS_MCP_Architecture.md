# 小红书 MCP (xhs-mcp) 架构分析与集成指南

> 当前使用 [ShunL12324/xhs-mcp](https://github.com/ShunL12324/xhs-mcp) (`@sillyl12324/xhs-mcp`)。
> 历史方案 [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp) 因登录稳定性问题已弃用。

---

## 目录

1. [核心架构](#核心架构)
2. [登录流程](#登录流程)
3. [AIInSight 集成现状](#aiinsight-集成现状)
4. [Docker 部署](#docker-部署)
5. [历史兼容说明](#历史兼容说明)

---

## 核心架构

### xhs-mcp 工作原理

ShunL12324/xhs-mcp 是一个 TypeScript + Playwright 的 MCP server，通过 headless Chromium 浏览器上下文调用小红书内部 API：

```
MCP Client → HTTP POST /mcp (StreamableHTTP) → xhs-mcp-entrypoint.mjs → @sillyl12324/xhs-mcp → Playwright headless Chromium → xiaohongshu.com 内部 API
```

### 与 xpzouying 的关键差异

| 特性 | xpzouying (旧) | ShunL12324 (新) |
|------|----------------|-----------------|
| 语言 | Go + go-rod | TypeScript + Playwright |
| 登录 | QR 扫码（无验证码支持） | QR 扫码 + 短信验证码 |
| 数据存储 | cookies.json 文件 | SQLite 数据库 |
| 多账号 | 不支持 | 支持账号池 |
| HTTP 协议 | JSON-RPC batch | StreamableHTTP (SSE) |
| Docker 运行时 | Go 二进制 | Node.js 20 (因 better-sqlite3 不支持 Bun) |

### MCP 工具映射

AIInSight 通过 `XiaohongshuPublisher._TOOL_NAME_MAP` 保持对外 API 兼容：

| AIInSight 内部名 | ShunL MCP 工具名 |
|------------------|-----------------|
| `get_login_qrcode` | `xhs_add_account` |
| `check_login_status` | `xhs_check_auth_status` |
| `publish_content` | `xhs_publish_content` |
| `list_feeds` | `xhs_list_feeds` |
| `delete_cookies` | `xhs_delete_cookies` |
| `search_feeds` | `xhs_search` |

---

## 登录流程

### 完整流程（支持短信验证码）

```
1. 调用 get_xhs_login_qrcode (→ xhs_add_account)
   返回: sessionId + qrCodeUrl

2. 用户用小红书 App 扫码

3. 调用 check_xhs_login_session(sessionId)
   返回: pending / need_verification / logged_in

4. 如果 need_verification:
   调用 submit_xhs_verification(sessionId, 短信验证码)

5. 登录完成，会话持久化到 SQLite
```

### 关键 MCP 工具

| MCP 工具名 | 说明 |
|------|------|
| `check_xhs_status` | 检查 sidecar 可用性和登录状态 |
| `get_xhs_login_qrcode` | 获取登录二维码 |
| `check_xhs_login_session` | 轮询扫码状态 |
| `submit_xhs_verification` | 提交短信验证码 |
| `publish_xhs_note` | 发布笔记到小红书 |
| `render_cards` | 渲染可视化卡片 |

---

## AIInSight 集成现状

### 架构

```
┌─────────────────────────────────┐
│ MCP Client (Copilot/Opencode)   │
│                                 │
│  skills: ai-insight,            │
│          ai-topic-analyzer      │
└───────────┬─────────────────────┘
            │ MCP (stdio/sse)
┌───────────▼─────────────────────┐
│ opinion_mcp (MCP Server :18061) │
│  public tools:                  │
│    render_cards                  │
│    publish_xhs_note              │
│    check_xhs_status              │
│    get_xhs_login_qrcode          │
│    check_xhs_login_session       │
│    submit_xhs_verification       │
└───────┬───────────┬─────────────┘
        │           │ direct HTTP
   ┌────▼────┐ ┌────▼──────────────┐
   │renderer │ │ xhs-mcp (Node.js) │
   │Playwright│ │ Playwright+SQLite │
   └─────────┘ └───────────────────┘
```

### 适配层

`XiaohongshuPublisher` (opinion_mcp/services/xiaohongshu_publisher.py) 作为适配层：
- `_TOOL_NAME_MAP` 字典将内部工具名映射到 ShunL 命名空间
- `_call_mcp()` 使用 StreamableHTTP 3-step handshake (initialize → notifications/initialized → tools/call)
- `_parse_sse_response()` 解析 SSE 格式响应 (`event: message\ndata: {JSON}`)

### 多账号适配

ShunL xhs-mcp 原生支持多账号（`account` 参数 + SQLite 隔离 + 多账号池管理）。适配层已完成 account-aware 改造：

- `_call_mcp(account=...)` — 非 None 时自动注入 `arguments["account"]` 到 ShunL MCP 调用
- 所有公共方法均支持可选 `account_id` 参数：`check_login_status`、`get_login_qrcode`、`publish_content`、`reset_login`、`submit_verification`、`check_login_session`、`get_status`
- `_login_session_ids: Dict[str, Optional[str]]` — 按 account_id 索引的 session 缓存
- `_login_qrcode_locks: Dict[str, asyncio.Lock]` — 按 account_id 隔离的 QR 生成锁
- `_get_login_qrcode_dir(account_id=...)` — 非 None 时返回 `outputs/xhs_login/{account_id}/` 子目录

调用链完整透传：

```
MCP Gateway (account_id from API key)
  → opinion_mcp/tools/publish.py (account_id param)
    → opinion_mcp/services/xiaohongshu_publisher.py (account_id → ShunL MCP "account" field)
```

不传 `account_id` 时所有行为与改造前完全一致（向后兼容）。

---

## Docker 部署

### 镜像构建

```bash
docker compose build xhs-mcp
```

基于 `Dockerfile.xhs-mcp`（Node.js 20 + Playwright Chromium）。入口是 `xhs-mcp-entrypoint.mjs`，用 `node:http` 替代原始 `Bun.serve()`。

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `XHS_MCP_HEADLESS` | `true` | 无头浏览器模式 |
| `XHS_MCP_DATA_DIR` | `/data` | SQLite 数据目录 |
| `XHS_MCP_PORT` | `18060` | HTTP 服务端口 |
| `XHS_MCP_REQUEST_INTERVAL` | `2000` | 请求间隔（毫秒） |
| `XHS_MCP_LOG_LEVEL` | `info` | 日志级别 |

### Volume 挂载

- `./runtime/xhs/data:/data` — SQLite 数据库持久化

### 启动命令

```bash
docker compose up -d --build mcp renderer xhs-mcp
```

---

## 历史兼容说明

仓库中保留的以下脚本属于旧版 xpzouying/xiaohongshu-mcp 方案，在 ShunL 方案下已不再需要：

- `scripts/build-xhs-mcp-image.sh` — 旧版 ARM64 镜像构建
- `scripts/xhs_login_local.py` — 旧版本地登录
- `scripts/start-xhs-mcp.sh` — 旧版 xpzouying 启动
- `scripts/check-xhs-mcp.sh` — 旧版健康检查

Cookie 注入相关代码 (`verify_and_save_cookies`, `_parse_raw_cookie_header` 等) 保留在 `XiaohongshuPublisher` 中作为降级路径。
