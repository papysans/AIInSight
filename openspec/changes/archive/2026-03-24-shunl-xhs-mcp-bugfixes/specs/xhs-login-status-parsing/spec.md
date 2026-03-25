## MODIFIED Requirements

### Requirement: 登录状态检查 SHALL 解析 ShunL JSON 结构而非字符串匹配

`XiaohongshuPublisher.check_login_status()` SHALL 将 ShunL `xhs_check_auth_status` 返回的 text content 作为 JSON 解析，并使用 `loggedIn` 布尔字段判断登录状态。当 text 不是合法 JSON 时，SHALL 降级为保守判断（视为未登录）。

#### Scenario: ShunL 返回 loggedIn: true
- **WHEN** ShunL 返回 `{"loggedIn": true, "message": "Logged in (user element found)", ...}`
- **THEN** `check_login_status()` MUST 返回 `{"logged_in": True, ...}`

#### Scenario: ShunL 返回 loggedIn: false
- **WHEN** ShunL 返回 `{"loggedIn": false, "message": "Not logged in (login button visible)", ...}`
- **THEN** `check_login_status()` MUST 返回 `{"logged_in": False, ...}`

#### Scenario: ShunL 返回非 JSON 文本
- **WHEN** ShunL 返回的 text content 不是合法 JSON
- **THEN** `check_login_status()` SHALL 降级为保守判断，返回 `{"logged_in": False, ...}`

### Requirement: AI Daily ranking 发布标题 SHALL 不超过 20 字符

AI Daily ranking 发布功能生成的标题 SHALL 自动适配 ShunL `xhs_publish_content` 的 20 字符限制。

#### Scenario: 自动生成的标题超过 20 字符
- **WHEN** AI Daily ranking 默认标题模板生成的标题超过 20 字符
- **THEN** 系统 MUST 使用缩短后的标题格式（如 `"M/DD AI热点榜Top10"`），确保不超过 20 字符

### Requirement: 渲染卡片图片 SHALL 对 xhs-mcp sidecar 可见

AI Daily ranking 发布时使用的渲染卡片图片 MUST 通过 API 容器与 `xhs-mcp` 容器共享的 volume 传递，确保 ShunL `xhs_publish_content` 能读取到实际图片文件。

#### Scenario: API 生成榜单卡片后调用发布
- **WHEN** API 将 data URL / 渲染结果落盘为图片文件
- **THEN** `xhs-mcp` sidecar MUST 能通过自己容器内的挂载路径访问同一批图片文件，而不能出现 `No valid image files found`

### Requirement: legacy publish 兼容层 SHALL 匹配当前发布页按钮 DOM

本地 `xhs-mcp-entrypoint.mjs` 复活的 `xhs_publish_content` 兼容工具 MUST 使用与当前小红书创作页一致的发布按钮 selector，而不能只依赖历史遗留的 `button.publishBtn`。

#### Scenario: 图文页面填写完成后点击发布
- **WHEN** 图片、标题、正文和标签都已填写完成
- **THEN** 兼容层 MUST 能在当前页面 DOM 中定位真实的发布按钮（当前已验证位于 `div.publish-page-publish-btn` 容器内），而不能报 `Publish button not found`

### Requirement: 发布结果 SHALL 暴露真实内层失败

`XiaohongshuPublisher.publish_content()` MUST 将 MCP tool 返回中的真实内层失败向上游暴露，而不能把 transport 成功误报为 publish 成功。

#### Scenario: MCP transport 成功但内层 publish 失败
- **WHEN** MCP 外层返回成功，但 text content 中的 JSON 为 `{"success": false, "error": "..."}` 或 `{"result": {"success": false, "error": "..."}}`
- **THEN** `publish_content()` MUST 返回 `success: false`，并保留真实错误信息供 API / MCP wrapper 消费
