## 1. xhs-mcp-entrypoint.mjs — 发布后回查验证

- [x] 1.1 实现 `verifyPublishViaCreatorCenter(client, title, timeoutMs)` 函数：等 5s → 查创作者中心最近 10 条 → 标题精确匹配 + 3 分钟时间窗口
- [x] 1.2 在 `handleLegacyPublishTool()` 中，`publishContent()` 返回 `success: true` 但无 `noteId` 时，调用回查验证
- [x] 1.3 回查匹配到 → 补 noteId，写 `db.published.record()`，返回真 success
- [x] 1.4 回查未匹配到 → 跳过 DB 写入，返回 `{ success: false, error: "submitted_but_unverified" }`
- [x] 1.5 回查异常 → 降级为 `submitted_but_unverified`，不返回假成功
- [x] 1.6 上游直接返回 noteId 时 → 信任并直接返回，跳过回查

## 2. opinion_mcp/tools/publish.py — 防御层

- [x] 2.1 `publish_xhs_note()` 中，上游返回 `success: true` 但 `note_url` 为 null 且无 noteId 可提取时，返回 `{ success: false, error: "submitted_but_unverified" }`

## 3. opinion_mcp/services/xiaohongshu_publisher.py — 超时修复

- [x] 3.1 `check_login_status` 超时从 30s 增至 60s

## 4. 验证

- [x] 4.1 `node --check xhs-mcp-entrypoint.mjs` 语法检查通过
- [x] 4.2 `python3 -c "import ast; ast.parse(open('opinion_mcp/tools/publish.py').read())"` 语法检查通过
- [x] 4.3 Docker build + up 成功
- [x] 4.4 扫码登录 → 发布笔记 → 确认返回真 noteId + note_url
- [x] 4.5 在小红书 App 确认笔记可见
