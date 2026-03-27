## 1. 验证与准备

- [x] 1.1 创建特性分支 `feat/shunl-xhs-mcp`，从 main 分支切出
- [x] 1.2 本地验证 `@sillyl12324/xhs-mcp` 是否支持 HTTP transport：`npx -y @sillyl12324/xhs-mcp@latest --help` 或阅读源码确认启动参数
- [x] 1.3 如果不支持 HTTP transport，编写 Node.js wrapper（stdio-to-http bridge）或 fork 项目添加 HTTP 支持
- [x] 1.4 本地启动 ShunL MCP 服务，用 MCP Inspector 测试 `xhs_add_account`、`xhs_check_login_session`、`xhs_submit_verification` 工具调用

## 2. Docker 配置

- [x] 2.1 创建 `Dockerfile.xhs-mcp`：基于 Node.js 20 slim + Playwright Chromium，入口为 ShunL MCP HTTP 模式
- [x] 2.2 更新 `docker-compose.yml` 中 `xhs-mcp` 服务定义：替换镜像、环境变量（`XHS_MCP_HEADLESS=true`, `XHS_MCP_DATA_DIR=/data`）、volume 挂载（`./runtime/xhs/data:/data`）
- [x] 2.3 更新 `docker-compose.xhs.yml` 同步修改
- [x] 2.4 验证 `docker compose up -d xhs-mcp` 容器正常启动并在 18060 端口响应 MCP 初始化请求

## 3. 适配层核心改造

- [x] 3.1 在 `XiaohongshuPublisher` 中添加工具名映射字典 `_TOOL_NAME_MAP`，将现有工具名映射到 ShunL 命名空间
- [x] 3.2 修改 `_call_mcp()` 方法：在构建 `tools/call` 请求前，通过映射字典转换工具名
- [x] 3.3 修改 `check_login_status()` 方法：适配 ShunL `xhs_check_auth_status` 的响应格式
- [x] 3.4 修改 `get_login_qrcode()` 方法：改为调用 `xhs_add_account`，缓存返回的 `sessionId`，提取 QR 码 URL/图片
- [x] 3.5 修改 `publish_content()` 方法：适配 `xhs_publish_content` 的参数格式（images 路径处理、tags 格式）
- [x] 3.6 修改 `reset_login()` 方法：改为调用 `xhs_delete_cookies`
- [x] 3.7 修改 `is_available()` 方法：确保健康检查兼容 ShunL MCP 的初始化响应

## 4. 短信验证码链路

- [x] 4.1 在 `XiaohongshuPublisher` 中新增 `submit_verification(session_id, code)` 方法，调用 `xhs_submit_verification`
- [x] 4.2 在 `app/api/endpoints.py` 中新增 `POST /api/xhs/submit-verification` 端点
- [x] 4.3 在 `app/schemas.py` 中新增请求/响应 schema（`XhsVerificationRequest`, `XhsVerificationResponse`）
- [x] 4.4 在 `opinion_mcp/tools/publish.py` 中新增 `submit_xhs_verification` MCP 工具函数
- [x] 4.5 在 `opinion_mcp/services/backend_client.py` 中新增 `submit_xhs_verification()` 方法调用后端 API
- [x] 4.6 修改登录状态检查逻辑：当 ShunL 返回 `need_verification` 时，在响应中包含 `session_id` 和验证码提示

## 5. MCP 工具注册

- [x] 5.1 在 MCP server 的工具注册逻辑中添加 `submit_xhs_verification` 工具定义（名称、描述、参数 schema）
- [x] 5.2 确保现有 MCP 工具名（`publish_to_xhs`, `check_xhs_status`, `get_xhs_login_qrcode`, `reset_xhs_login`）的注册和行为不变

## 6. 环境变量与配置

- [x] 6.1 更新 `.env.example`：新增 `XHS_MCP_HEADLESS`, `XHS_MCP_DATA_DIR`, `XHS_MCP_REQUEST_INTERVAL` 环境变量说明
- [x] 6.2 更新 `app/config.py` 和 `opinion_mcp/config.py` 中 XHS 相关配置（如有需要）
- [x] 6.3 清理不再需要的环境变量引用（`ROD_BROWSER_BIN`, `COOKIES_PATH` 等 xpzouying 特有的）

## 7. 集成测试与验证

- [x] 7.1 Docker 四服务启动测试：`docker compose up -d --build api mcp renderer xhs-mcp`
- [x] 7.2 测试完整登录流程：QR 扫码 → 可选短信验证码 → 登录成功
- [ ] 7.3 测试发布流程：调用 `publish_to_xhs` 或 `/api/xhs/publish` 发布一篇测试图文（需单独批准的真实外部副作用 canary 验证）
- [x] 7.4 测试状态检查：`GET /api/xhs/status` 返回正确的服务可用性和登录状态
- [x] 7.5 测试容器重启后会话保持：重启 xhs-mcp 容器后检查登录状态是否保留

## 8. 文档与清理

- [x] 8.1 更新 `README.md` 中小红书发布相关说明（镜像变更、新增验证码流程）
- [x] 8.2 更新 `docs/XHS_MCP_Architecture.md` 架构文档
- [x] 8.3 更新 `scripts/` 下的辅助脚本（如果有需要适配的）
- [x] 8.4 标记或移除不再需要的 xpzouying 相关脚本（`build-xhs-mcp-image.sh`, `xhs_login_local.py` 等）

## 9. 多账号适配（为 cloud-remote-mcp-gateway 做前置准备）

ShunL xhs-mcp 原生支持多账号（`account` 参数 + SQLite 隔离 + 多账号池管理），但当前适配层未暴露此能力。以下任务将适配层改造为 account-aware，使云端多用户部署成为可能。

### 9.1 适配层 account 透传

- [x] 9.1.1 `_call_mcp()` 新增可选 `account: Optional[str]` 参数，非 None 时自动注入到 ShunL MCP 调用的 `arguments["account"]`
- [x] 9.1.2 `check_login_status()` 新增可选 `account_id: Optional[str]` 参数，透传到 `_call_mcp(account=account_id)`
- [x] 9.1.3 `get_login_qrcode()` 新增可选 `account_id: Optional[str]` 参数，透传到 `_call_mcp(account=account_id)`
- [x] 9.1.4 `publish_content()` 新增可选 `account_id: Optional[str]` 参数，透传到 `_call_mcp(account=account_id)`
- [x] 9.1.5 `reset_login()` 新增可选 `account_id: Optional[str]` 参数，透传到 `_call_mcp(account=account_id)`
- [x] 9.1.6 `submit_verification()` 新增可选 `account_id: Optional[str]` 参数，透传到 `_call_mcp(account=account_id)`
- [x] 9.1.7 `check_login_session()` 新增可选 `account_id: Optional[str]` 参数，透传到 `_call_mcp(account=account_id)`
- [x] 9.1.8 `get_status()` 新增可选 `account_id: Optional[str]` 参数，透传到内部调用

### 9.2 per-account 状态隔离

- [x] 9.2.1 `_login_session_id` 从 `Optional[str]` 改为 `Dict[str, Optional[str]]`，按 `account_id` 索引（None account_id 用 `"_default"` key）
- [x] 9.2.2 `_get_login_qrcode_dir()` 支持可选 `account_id` 参数，有值时返回 `outputs/xhs_login/{account_id}/` 子目录
- [x] 9.2.3 `_save_login_qrcode_meta()` / `_load_cached_login_qrcode()` 按 `account_id` 隔离元数据文件（消除全局 `latest.json`）
- [x] 9.2.4 `_login_qrcode_lock` 从全局单锁改为按 `account_id` 分锁（避免不同用户互相阻塞 QR 生成）

### 9.3 上层调用链 account 透传

- [x] 9.3.1 `app/api/endpoints.py` 中 XHS 相关端点（`/api/xhs/status`, `/api/xhs/login-qrcode`, `/api/xhs/submit-verification`, `/api/xhs/publish` 等）新增可选 `account_id` query/header 参数，透传到 `XiaohongshuPublisher`
- [x] 9.3.2 `opinion_mcp/tools/publish.py` 中 MCP 工具函数（`check_xhs_status`, `get_xhs_login_qrcode`, `publish_to_xhs`, `submit_xhs_verification` 等）新增可选 `account_id` 参数，透传到 backend_client
- [x] 9.3.3 `opinion_mcp/services/backend_client.py` 中 XHS 相关方法新增可选 `account_id` 参数，作为 query param 或 header 传递给后端 API

### 9.4 验证

- [x] 9.4.1 不传 `account_id` 时所有现有行为不变（向后兼容）
- [x] 9.4.2 传不同 `account_id` 时，ShunL sidecar 创建独立的登录 session（可通过 `xhs_add_account` 调用两次不同 account 名验证）
- [x] 9.4.3 更新 `docs/XHS_MCP_Architecture.md` 增加多账号适配说明
