# Proposal: XHS Publish Verification Gate

## Problem

当前 XHS 发布链路存在**假成功**问题。整条链路从上游 xhs-mcp 到我们的 opinion_mcp 都在做乐观判定，导致用户收到 `{"success": true, "note_url": null}`，但实际上笔记在小红书前台不可见。

### 根因（从上游源码确认）

**xhs-mcp `publish.ts` L173-189：**

```typescript
await publishBtn.click();
await sleep(3000);
const resultUrl = page.url();

if (resultUrl.includes('success') || resultUrl.includes('publish')) {
    const noteIdMatch = resultUrl.match(/note\/([a-zA-Z0-9]+)/);
    return { success: true, noteId: noteIdMatch?.[1] };  // noteId 永远是 undefined
}
return { success: true };  // 兜底也是 success
```

- `resultUrl.includes('publish')` 是**永真条件**（发布页 URL 本身就含 `publish`）
- `note/([a-zA-Z0-9]+)` 正则在发布页 URL 中永远匹配不到
- 结果：`{ success: true, noteId: undefined }` → 数据库记录 `note_id: null`

**我们侧 `publish_xhs_note()` L139-142：**

```python
result_payload = {"success": True, "note_url": note_url}
if not note_url:
    result_payload["message"] = "已发布成功，但上游未返回 note_url..."
return result_payload  # 仍然 success: true
```

## Solution

**方案 C（包装 + 回查）**：不 fork 上游，在 `xhs-mcp-entrypoint.mjs` 的 `handleLegacyPublishTool` 中追加回查验证。同时在 `opinion_mcp` 层加防御。

### 核心改动

#### 1. `xhs-mcp-entrypoint.mjs` — 发布后回查验证

在 `handleLegacyPublishTool()` 中，`publishContent()` 返回后：

```
publishContent() 返回
    │
    ▼
result.noteId 有值？ ─── yes ──→ 真 success（写 db，返回 noteId）
    │
    no
    ▼
sleep(5s) 等平台同步
    │
    ▼
ctx.client.getMyPublishedNotes(tab=0, limit=5, timeout=15000)
    │
    ▼
标题匹配到新笔记？
    ├─ yes → 补 noteId，真 success
    └─ no  → { success: false, error: "submitted_but_unverified" }
```

关键设计决策：
- 回查用 `getMyPublishedNotes()`（创作者中心 API），**不用全站搜索**（超时风险）
- 只取最近 5 条，用标题精确匹配
- 5 秒等待是给小红书平台侧同步的时间窗口
- `db.published.record()` 延迟到回查确认后才写

#### 2. `opinion_mcp/tools/publish.py` — 防御层

即使上游改好了，我们侧也加一道防线：
- `note_url` 为 null 且上游无 error 时，返回 `success: false, error: "submitted_but_unverified"`
- 不再把"拿不到 note_url"当成成功

### 不改什么

- 不 fork xhs-mcp 仓库
- 不改 `@sillyl12324/xhs-mcp` npm 包
- 不改 Dockerfile.xhs-mcp
- 不改 docker-compose.yml

## Scope

| 文件 | 改动内容 |
|------|---------|
| `xhs-mcp-entrypoint.mjs` | `handleLegacyPublishTool()` 追加回查逻辑 (~40行) |
| `opinion_mcp/tools/publish.py` | `publish_xhs_note()` 防御层 (~10行) |

## Risks

1. **回查延迟**：小红书平台侧可能需要 >5s 才同步到创作者中心 → 可调整等待时间
2. **getMyPublishedNotes 失败**：浏览器自动化可能因页面变化而失败 → 失败时降级为 `submitted_but_unverified`，不返回假成功
3. **标题匹配误判**：用户连续发两条同标题笔记时可能匹配错 → 可结合发布时间窗口过滤

## Verification

需要端到端测试：
1. 渲染卡片 → 发布到小红书 → 确认返回真 noteId + note_url
2. 登录过期场景 → 确认不会返回假成功
3. 网络异常场景 → 确认回查超时后返回 `submitted_but_unverified`

**需要用户配合**：测试需要真实小红书账号扫码登录 + 实际发布。
