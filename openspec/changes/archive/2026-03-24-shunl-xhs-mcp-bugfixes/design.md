## Context

ShunL xhs-mcp 的 `xhs_check_auth_status` 返回的 text content 是 JSON 字符串，格式如下：

已登录时：
```json
{
  "account": "小红薯6975F30A",
  "loggedIn": true,
  "message": "Logged in (user element found)",
  "userInfo": { "userId": "...", "nickname": "..." },
  "profileSynced": true
}
```

未登录时：
```json
{
  "account": "小红薯6975F30A",
  "loggedIn": false,
  "message": "Not logged in (login button visible)",
  "profileSynced": false,
  "hint": "Please use xhs_add_account to login."
}
```

当前代码（`check_login_status` 第 510 行）使用 `"logged in" in text.lower()` 匹配，但 `"Not logged in"` 也包含 `"logged in"` 子串，导致未登录被误判为已登录。

后续联调又暴露出第二层问题：

1. API 生成的 AI Daily 榜单卡片会被 `_process_image()` 写入 `./runtime/xhs/images`，但 `xhs-mcp` 容器最初没有挂载该目录，导致 ShunL 报 `No valid image files found`
2. 本地 `xhs-mcp-entrypoint.mjs` 复活的 legacy `xhs_publish_content` 兼容工具虽然保住了旧工具名，但内部 selector 仍停留在旧版页面：
   - 上传图文 tab 仍使用老的 `div.creator-tab` + 文字点击逻辑
   - 发布按钮仍使用 `button.publishBtn`
   - 写库时使用非法 `noteType='normal'`

实际 DOM 检查显示，当前小红书创作页在图文模式下的真实发布按钮位于：

```html
<div class="publish-page-publish-btn">
  <button class="d-button ... custom-button bg-red">发布</button>
</div>
```

因此问题不是“ShunL 不支持发布”，而是我们的本地 legacy compatibility layer 与当前页面结构发生了漂移。

## Decisions

### D1: 登录状态解析改为 JSON 字段

**选项 A（✅ 选定）**：解析 ShunL 返回的 JSON，直接读取 `loggedIn` 布尔字段
- 最可靠，不受 message 措辞变化影响
- 需要 try/except 处理非 JSON 响应的降级

**选项 B**：改进字符串匹配（排除 "Not logged in"）
- 脆弱，依赖 ShunL 的措辞不变

### D2: 标题长度处理

**选项 A（✅ 选定）**：在 AI Daily ranking 发布入口自动生成符合 20 字符限制的标题
- 例如 `"3/24 AI热点榜Top10"` 或 `"0324AI热点Top10"`
- 不改 ShunL 的限制（那是小红书平台的限制）

**选项 B**：在 `publish_content` 通用层截断
- 影响面太广，可能截断用户有意义的标题

### D3: 卡片图片传递必须使用共享卷而非容器内临时路径

**选项 A（✅ 选定）**：API 与 `xhs-mcp` 通过共享 volume 传递渲染后的卡片图片
- API 写入 `./runtime/xhs/images`
- `xhs-mcp` 将同一宿主目录挂载为 `/app/images`
- `_process_image()` 返回 ShunL 可见的绝对路径 `/app/images/...`

**选项 B**：继续使用 `/tmp` 或单容器内路径
- 在双容器部署下天然不可见
- 不能可靠支撑渲染服务与发布 sidecar 分离的架构

### D4: 继续使用 legacy `xhs_publish_content`，但在本地兼容层打补丁

**选项 A（✅ 选定）**：保留 AIInSight 当前 `publish_content -> xhs_publish_content` 调用契约，在本地 `xhs-mcp-entrypoint.mjs` 里修复 selector 与写库值
- 风险最小，不改变上层接口
- 只修复当前已确认失效的兼容层实现
- 配合 DOM 证据将 selector 从 `button.publishBtn` 扩展为 `button.publishBtn, div.publish-page-publish-btn button.bg-red`

**选项 B**：立即切换到 `xhs_create_draft + xhs_publish_draft`
- 经过源码审查，`xhs_publish_draft` 最终仍调用 `ctx.client.publishContent(...)`
- 不能绕开当前的 publish page selector 问题
- 会引入更大范围的 AIInSight adapter 改造，不符合本次 bugfix 的最小修复原则

### D5: 发布结果必须在 Python 集成边界归一化

`XiaohongshuPublisher.publish_content()` 不能把“transport 成功”误当成“发布成功”。当内层 JSON 返回以下任一形态时，都必须向上游暴露失败：

```json
{"success": false, "error": "..."}
```

或

```json
{"result": {"success": false, "error": "..."}}
```

这样 API / MCP wrapper 才能看到真实发布结果，而不是被兼容层的外层成功包裹误导。

## Risks

- 极低到中等风险的 bugfix：登录状态与结果归一化是低风险；本地 selector patch 依赖当前页面 DOM，后续若页面再次改版需要重新同步
- ShunL 未来如果改变 JSON 格式需要同步更新解析逻辑
- legacy publish 兼容工具本身属于 AIInSight 本地补层，需要持续跟踪上游页面结构变化
