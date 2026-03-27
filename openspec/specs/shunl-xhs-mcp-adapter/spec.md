## ADDED Requirements

### Requirement: MCP 工具名映射

`XiaohongshuPublisher._call_mcp()` SHALL 将现有工具名映射到 ShunL xhs-mcp 的命名空间：

| 现有工具名 | ShunL 工具名 |
|-----------|-------------|
| `get_login_qrcode` | `xhs_add_account` |
| `check_login_status` | `xhs_check_auth_status` |
| `publish_content` | `xhs_publish_content` |
| `list_feeds` | `xhs_list_feeds` |
| `delete_cookies` | `xhs_delete_cookies` |
| `search_feeds` | `xhs_search` |

映射 SHALL 在适配层内部完成，上层调用者 MUST NOT 需要感知工具名变化。

#### Scenario: 调用 publish_content 时自动映射

- **WHEN** `XiaohongshuPublisher.publish_content()` 调用 `_call_mcp("publish_content", ...)`
- **THEN** 实际发送到 ShunL MCP 的工具名为 `xhs_publish_content`

#### Scenario: 调用 check_login_status 时自动映射

- **WHEN** `XiaohongshuPublisher.check_login_status()` 调用 `_call_mcp("check_login_status")`
- **THEN** 实际发送到 ShunL MCP 的工具名为 `xhs_check_auth_status`

### Requirement: 响应格式适配

ShunL MCP 的响应格式与 xpzouying 可能不同。适配层 SHALL 将 ShunL 的响应统一转换为现有代码期望的格式：
- MCP 标准响应格式 `{"content": [{"type": "text", "text": "..."}]}`
- 登录状态判定逻辑（从响应文本中提取"已登录"/"logged in"）
- 发布结果提取（笔记 URL、成功/失败）

#### Scenario: 发布成功时提取笔记 URL

- **WHEN** ShunL MCP 返回发布成功的响应
- **THEN** 适配层提取出笔记 URL 并以现有格式返回 `{"success": True, "message": "...", "data": {...}}`

#### Scenario: 登录状态检查解析

- **WHEN** 调用 `check_login_status` 并 ShunL 返回账号已认证
- **THEN** 适配层返回 `{"success": True, "logged_in": True, "message": "..."}`

### Requirement: Docker Compose 服务定义

`docker-compose.yml` 和 `docker-compose.xhs.yml` 中的 `xhs-mcp` 服务 SHALL 替换为 ShunL xhs-mcp 容器，保持服务名 `xhs-mcp` 和端口 `18060` 不变。

#### Scenario: Docker Compose 启动四服务

- **WHEN** 执行 `docker compose up -d --build api mcp renderer xhs-mcp`
- **THEN** xhs-mcp 容器使用 ShunL 的 Node.js + Playwright 镜像正常启动，暴露 18060 端口
