## Why

当前项目使用 xpzouying/xiaohongshu-mcp (Go) 作为小红书 sidecar，近期小红书平台在 headless 浏览器环境下增强了扫码登录的短信验证码环节，导致：

1. 扫码成功后收到验证码但无处输入（GitHub Issues #517, #554 大量复现）
2. Session 状态机异常，tools/call 全部失败（#554）
3. Docker 容器 120 秒自动退出（#515）

核心痛点：**xpzouying 没有短信验证码提交能力**，而小红书对 headless 环境会触发短信验证。

ShunL12324/xhs-mcp（@sillyl12324/xhs-mcp）是目前唯一支持 `xhs_submit_verification`（程序化提交短信验证码）的 XHS MCP 方案，且具备：
- 多账号池管理 + 并发保护
- SQLite 会话持久化，重启不丢登录态
- `XHS_MCP_HEADLESS=true` 环境变量，天然适配 Docker/云端无人值守
- Playwright 驱动 + TypeScript + npm 已发包

## What Changes

- **新增** ShunL12324/xhs-mcp 作为 XHS MCP 后端，替代 xpzouying/xiaohongshu-mcp
- **新增** 适配层：将 ShunL 的 MCP 工具名（`xhs_*` 命名空间）映射到现有 `XiaohongshuPublisher` 接口
- **新增** 短信验证码提交链路（API 端点 + MCP 工具）
- **新增** ShunL xhs-mcp 的 Dockerfile 和 Docker Compose 配置
- **修改** `XiaohongshuPublisher._call_mcp()` 适配 ShunL 的 MCP 响应格式
- **修改** `docker-compose.yml` 和 `docker-compose.xhs.yml` 中 xhs-mcp 服务定义
- **修改** 登录链路：支持 QR 扫码 → 短信验证码 → 登录完成的完整流程
- **保留** 现有 API 端点路径（`/api/xhs/status`, `/api/xhs/login-qrcode` 等）和 MCP 工具名（`publish_to_xhs`, `check_xhs_status` 等）不变，对外无感知切换

## Capabilities

### New Capabilities
- `shunl-xhs-mcp-adapter`: ShunL xhs-mcp 的适配集成层，包含 MCP 工具名映射、响应格式转换、Docker 配置
- `xhs-sms-verification`: 短信验证码提交链路，解决 headless 环境下扫码后被要求验证码的问题

### Modified Capabilities
- `cookie-based-xhs-auth`: 登录认证流程从纯 QR 扫码扩展为 QR 扫码 + 可选短信验证码
- `docker-first-official-xhs-runtime`: Docker sidecar 从 xpzouying Go 镜像切换为 ShunL TypeScript + Playwright 镜像

## Impact

- **代码影响**: `app/services/xiaohongshu_publisher.py`（核心适配层）、`app/api/endpoints.py`（新增验证码端点）、`opinion_mcp/tools/publish.py`（新增 MCP 工具）、`docker-compose*.yml`
- **依赖变化**: 从 Go 二进制 → Node.js/npx `@sillyl12324/xhs-mcp`，Dockerfile 需要 Node.js + Playwright + Chromium
- **API 兼容性**: 对外 HTTP 端点和 MCP 工具名保持不变，新增 `/api/xhs/submit-verification` 端点
- **数据迁移**: 旧 cookies.json（go-rod 格式）不兼容新方案（SQLite），需重新登录
- **环境变量**: 新增 `XHS_MCP_HEADLESS`, `XHS_MCP_DATA_DIR`, `XHS_MCP_REQUEST_INTERVAL`；`XHS_MCP_URL` 含义不变
