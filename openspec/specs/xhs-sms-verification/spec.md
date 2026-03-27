## ADDED Requirements

### Requirement: 短信验证码提交 API 端点

系统 SHALL 新增 `POST /api/xhs/submit-verification` HTTP 端点，接受 `session_id` 和 `code` 参数，调用 ShunL MCP 的 `xhs_submit_verification` 工具。

请求体格式：
```json
{
  "session_id": "string",
  "code": "string"
}
```

#### Scenario: 成功提交验证码

- **WHEN** 用户扫码后收到短信验证码，调用 `POST /api/xhs/submit-verification` 提交正确验证码
- **THEN** 系统调用 `xhs_submit_verification`，返回 `{"success": true, "message": "验证码提交成功，登录完成"}`

#### Scenario: 验证码错误

- **WHEN** 用户提交错误的验证码
- **THEN** 系统返回 `{"success": false, "message": "验证码错误，请重试"}`

#### Scenario: session_id 无效或过期

- **WHEN** 用户提交的 session_id 不存在或已过期
- **THEN** 系统返回 `{"success": false, "message": "登录会话已过期，请重新扫码"}`

### Requirement: 短信验证码 MCP 工具

系统 SHALL 新增 `submit_xhs_verification` MCP 工具（在 opinion_mcp/tools/publish.py 中注册），供 AI 助手直接调用。

工具参数：
- `session_id` (string, required): 登录会话 ID
- `code` (string, required): 短信验证码

#### Scenario: AI 助手提交验证码

- **WHEN** AI 助手调用 `submit_xhs_verification(session_id="xxx", code="123456")`
- **THEN** 系统通过 backend_client 调用 `POST /api/xhs/submit-verification`，返回登录结果

### Requirement: 登录流程中的验证码提示

当 `xhs_check_login_session` 返回需要验证码时，系统 SHALL 在响应中明确提示用户查看手机短信并提供验证码。

#### Scenario: 扫码后需要验证码

- **WHEN** 用户扫码后，`check_login_status` / 轮询返回 `need_verification` 状态
- **THEN** 响应包含 `{"login_status": false, "need_verification": true, "session_id": "xxx", "message": "请查看手机短信，输入收到的验证码。调用 submit_xhs_verification 或 POST /api/xhs/submit-verification 提交。"}`

#### Scenario: 扫码后直接登录成功（无需验证码）

- **WHEN** 用户扫码后，小红书未要求短信验证
- **THEN** 直接返回 `{"login_status": true, "message": "登录成功"}`，不出现验证码提示
