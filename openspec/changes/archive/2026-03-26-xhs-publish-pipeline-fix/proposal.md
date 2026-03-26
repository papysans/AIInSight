## Why

XHS 发布链路存在**假成功**问题。上游 xhs-mcp 的 `publishContent()` 在点击发布按钮后仅等待 3 秒，用 `resultUrl.includes('publish')` 判断成功——这是永真条件（发布页 URL 本身含 `publish`），导致永远返回 `{ success: true, noteId: undefined }`。我们侧 `opinion_mcp` 也在乐观透传这个结果，用户收到 `success: true` 但笔记实际未发布。

经 E2E 验证，通过在 entrypoint 层追加创作者中心回查 + opinion_mcp 层加防御，已成功拦截假成功并在真实发布场景下回查到 noteId。现需将这些修复正式固化。

## What Changes

- **xhs-mcp-entrypoint.mjs**: 在 `handleLegacyPublishTool()` 中追加发布后回查验证（通过创作者中心 `getMyPublishedNotes` API），用标题匹配 + 时间窗口确认 noteId
- **opinion_mcp/tools/publish.py**: 防御层——上游返回 `success: true` 但 `note_url` 为空时，改返回 `success: false, error: "submitted_but_unverified"`
- **opinion_mcp/services/xiaohongshu_publisher.py**: `check_login_status` 超时从 30s 增至 60s，避免在 Docker 环境下因浏览器启动慢导致误判未登录
- **xhs-mcp-entrypoint.mjs**: 移除 unverified 场景下的 `db.published.record()` 调用（SQLite CHECK 约束不允许 `status: 'unverified'`）

## Capabilities

### New Capabilities
- `xhs-publish-verification-gate`: 发布后通过创作者中心 API 回查验证，消除假成功。未验证时返回明确错误而非假成功。

### Modified Capabilities
- `xhs-publish-result-normalization`: 当上游返回 `success: true` 但无法提取任何 identifier 时，结果从"成功+提示消息"改为"失败+submitted_but_unverified 错误码"。**BREAKING**: 之前 `note_url: null` 仍返回 `success: true`，现在返回 `success: false`。

## Impact

- **xhs-mcp-entrypoint.mjs**: 新增 `verifyPublishViaCreatorCenter()` 函数 (~35行)，修改 `handleLegacyPublishTool()` 逻辑
- **opinion_mcp/tools/publish.py**: `publish_xhs_note()` 结果处理逻辑变更
- **opinion_mcp/services/xiaohongshu_publisher.py**: 超时参数调整
- **下游影响**: 依赖 `publish_xhs_note` 返回值的调用方需适配 `submitted_but_unverified` 错误码
- **发布耗时增加**: 回查增加 ~20s（5s 等待 + 15s 创作者中心查询）
