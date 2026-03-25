## Context

当前 AIInSight 通过 `XiaohongshuPublisher` 类 (`app/services/xiaohongshu_publisher.py`) 与 xpzouying/xiaohongshu-mcp (Go) Docker sidecar 交互。交互协议为 JSON-RPC 2.0 批处理模式（每次调用发送 initialize + notifications/initialized + tools/call 三条消息）。

现有链路：
```
opinion_mcp/tools/publish.py → backend_client → API endpoints → XiaohongshuPublisher._call_mcp() → HTTP POST → xhs-mcp:18060/mcp (Go)
```

xpzouying 的 MCP 工具名：`get_login_qrcode`, `check_login_status`, `publish_content`, `list_feeds`, `delete_cookies`

ShunL12324 的 MCP 工具名：`xhs_add_account`, `xhs_check_login_session`, `xhs_submit_verification`, `xhs_publish_content`, `xhs_search`, `xhs_list_feeds`, `xhs_get_note`, `xhs_like_feed` 等

关键差异：
1. **工具名不同**：ShunL 使用 `xhs_` 前缀命名空间
2. **登录流程不同**：ShunL 是 `xhs_add_account` → QR → `xhs_check_login_session` → 可选 `xhs_submit_verification`
3. **多账号**：ShunL 支持多账号，所有操作可指定 `account` 参数
4. **传输协议**：ShunL 使用 stdio 模式（npx 进程），需改为 HTTP 模式或保持 stdio
5. **存储**：ShunL 用 SQLite (`~/.xhs-mcp/data.db`)，xpzouying 用 `cookies.json`

## Goals / Non-Goals

**Goals:**
- 将 XHS MCP 后端从 xpzouying 切换为 ShunL12324，解决短信验证码登录问题
- 保持现有 API 端点路径和 MCP 工具名不变，对上层无感知
- 支持 Docker 容器化部署，headless 模式运行
- 新增短信验证码提交链路
- 在独立分支上进行，不影响 main 分支稳定性

**Non-Goals:**
- 不做多账号管理功能暴露（ShunL 支持但当前不需要）— **注：此约束已被 `cloud-remote-mcp-gateway` change 推翻，该 change 的 D6 决策要求暴露 ShunL 的多账号能力以支持云端多用户隔离**
- 不迁移旧 cookies 数据（需重新登录）
- 不改动 AI Daily / Topic 分析链路
- 不做 AI 图片生成功能集成（ShunL 的 Gemini 集成）
- 不做互动功能暴露（点赞、收藏、评论）

## Decisions

### D1: MCP 通信方式 — 选择 HTTP StreamableHTTP

**选项 A**: stdio 模式（npx 子进程）
- 优点：零网络配置
- 缺点：Docker sidecar 模式不适合 stdio；需要 npx 在主容器中运行；进程管理复杂

**选项 B (✅ 选定)**: HTTP 模式
- ShunL 的 `@sillyl12324/xhs-mcp` 虽然 README 里只展示了 stdio，但底层用的是 `@modelcontextprotocol/sdk`，支持 StreamableHTTP
- 保持和现有 xpzouying 一样的 sidecar HTTP 模式，`XiaohongshuPublisher._call_mcp()` 的批处理逻辑可以最大限度复用
- 容器独立运行，通过 `http://xhs-mcp:18060/mcp` 访问

**理由**: Docker 架构一致性，最小化改动。

### D2: 适配层位置 — XiaohongshuPublisher 内部适配

**选项 A**: 新建适配类 `ShunLXhsAdapter`
- 优点：隔离清晰
- 缺点：需要重构上层调用链

**选项 B (✅ 选定)**: 在 `XiaohongshuPublisher` 内部修改 `_call_mcp` + 各方法
- 修改工具名映射（`publish_content` → `xhs_publish_content`）
- 修改响应解析（适配 ShunL 的返回格式）
- 新增 `submit_verification` 方法
- 保持外部接口完全不变

**理由**: 改动最小，XiaohongshuPublisher 本身就是适配层的定位。

### D3: Dockerfile 方案 — 基于 Node.js + Playwright

```dockerfile
FROM node:20-slim
RUN npx -y playwright install --with-deps chromium
# ShunL 的 MCP 通过 npx 运行，数据存储在 /data
ENV XHS_MCP_DATA_DIR=/data
ENV XHS_MCP_HEADLESS=true
EXPOSE 18060
CMD ["npx", "-y", "@sillyl12324/xhs-mcp@latest"]
```

需要验证 ShunL 的包是否支持 HTTP transport 启动参数。如果不支持，需要 fork 或 wrapper。

### D4: 登录流程改造

现有流程：`get_login_qrcode` → 用户扫码 → `check_login_status` → (卡住)

新流程：
1. `xhs_add_account` → 返回 `sessionId` + `qrCodeUrl`
2. 用户扫码
3. `xhs_check_login_session({ sessionId })` → 返回 `pending` / `need_verification` / `logged_in`
4. 如果 `need_verification`：
   - 新增 `POST /api/xhs/submit-verification` 端点
   - 调用 `xhs_submit_verification({ sessionId, code })`
5. 登录完成，会话持久化到 SQLite

关键：需要保持 `sessionId` 状态在多次 HTTP 调用间传递。

## Risks / Trade-offs

1. **[ShunL HTTP 支持不确定]** → 需先验证 `@sillyl12324/xhs-mcp` 是否支持 HTTP transport。如不支持，Plan B：在容器内用 Node.js wrapper 将 stdio MCP 转为 HTTP。

2. **[ShunL 项目活跃度低 (8 stars)]** → 如果项目停更，需要 fork 维护。缓解：代码量不大（TypeScript），可以自行维护。

3. **[MCP 协议版本差异]** → ShunL 用的 MCP SDK 版本可能和 xpzouying 不同，批处理请求格式可能不兼容。需要在适配层处理。

4. **[短信验证码 UX]** → 在 TUI/CLI 场景下，需要让用户知道去手机查看验证码并输入。需要在 MCP 工具返回中明确提示。

5. **[数据迁移]** → 旧 cookies.json 不可复用，用户需要重新登录。可接受但需在文档中说明。
