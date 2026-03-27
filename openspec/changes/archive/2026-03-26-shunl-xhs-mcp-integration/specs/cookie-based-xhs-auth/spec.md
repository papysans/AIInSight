## MODIFIED Requirements

### Requirement: 登录二维码获取

登录流程从 xpzouying 的 `get_login_qrcode` 单步操作改为 ShunL 的两步操作：`xhs_add_account`（获取 sessionId + QR）→ `xhs_check_login_session`（轮询状态）。

外部 API 端点 `GET /api/xhs/login-qrcode` MUST 保持不变，内部实现改为调用 ShunL MCP 的 `xhs_add_account`。

返回的 `session_id` SHALL 被缓存，供后续 `check_qrcode_status` 和 `submit_verification` 使用。

#### Scenario: 获取登录二维码

- **WHEN** 调用 `GET /api/xhs/login-qrcode`
- **THEN** 内部调用 `xhs_add_account`，返回 QR 码图片/URL 和 `session_id`，格式兼容现有 `XhsLoginQrcodeResponse`

#### Scenario: 已登录时获取二维码

- **WHEN** 调用 `GET /api/xhs/login-qrcode` 但用户已登录
- **THEN** 返回 `{"success": true, "already_logged_in": true, "message": "已登录，无需扫码"}`

### Requirement: 登录状态检查

`GET /api/xhs/status` 和 `check_xhs_status` MCP 工具 MUST 继续工作，内部改为调用 ShunL 的 `xhs_check_auth_status`。

#### Scenario: 检查已登录状态

- **WHEN** 调用 `GET /api/xhs/status` 且 ShunL 报告账号已认证
- **THEN** 返回 `{"mcp_available": true, "login_status": true, "message": "..."}`

#### Scenario: 检查未登录状态

- **WHEN** 调用 `GET /api/xhs/status` 且无已认证账号
- **THEN** 返回 `{"mcp_available": true, "login_status": false, "message": "..."}`

### Requirement: Cookie 持久化方式变更

存储从 `cookies.json` 文件改为 ShunL 的 SQLite 数据库 (`~/.xhs-mcp/data.db`)。旧的 cookie 上传接口 (`POST /api/xhs/upload-cookies`) 可以保留但标记为 deprecated。

#### Scenario: 重启后会话保持

- **WHEN** xhs-mcp 容器重启
- **THEN** SQLite 中的会话数据通过 volume 挂载持久化，无需重新登录
