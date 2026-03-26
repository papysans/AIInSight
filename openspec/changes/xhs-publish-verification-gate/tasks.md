# Tasks: XHS Publish Verification Gate

## 1. entrypoint 回查逻辑

- [ ] 1.1 在 `handleLegacyPublishTool()` 中，`publishContent()` 返回 `success: true` 但 `noteId` 为空时，追加 `getMyPublishedNotes(tab=0, limit=5, timeout=15000)` 回查
- [ ] 1.2 回查前 sleep 5s 等待平台同步
- [ ] 1.3 用标题精确匹配 + 发布时间窗口（2分钟内）筛选新笔记
- [ ] 1.4 匹配到 → 提取 noteId，构造 note_url，`db.published.record()` 写入正确的 noteId
- [ ] 1.5 未匹配到 → 返回 `{ success: false, error: "submitted_but_unverified", message: "发布动作已提交，但未在创作者中心确认到新笔记" }`
- [ ] 1.6 回查本身抛异常 → 降级返回 `submitted_but_unverified`，不返回假成功
- [ ] 1.7 `db.published.record()` 延迟到回查确认后执行；未确认时 status 设为 `unverified`

## 2. opinion_mcp 防御层

- [ ] 2.1 `publish_xhs_note()` 中，当上游返回 `success: true` 但 `note_url` 为 null 且无 noteId 可提取时，改返回 `success: false, error: "submitted_but_unverified"`

## 3. 端到端验证（需用户配合）

- [ ] 3.1 docker compose build + up
- [ ] 3.2 扫码登录小红书
- [ ] 3.3 渲染卡片 → 调用 publish_xhs_note 发布 → 确认返回 noteId + note_url
- [ ] 3.4 在小红书 App 确认笔记可见
- [ ] 3.5 测试故意传错 account_id → 确认不返回假成功
