## Context

当前发布链路架构：`opinion_mcp (Python)` → `xhs-mcp-entrypoint.mjs (Node.js wrapper)` → `@sillyl12324/xhs-mcp (npm, Playwright 自动化)`。

上游 `publishContent()` 在点击发布按钮后用 `resultUrl.includes('publish')` 判断——永真条件，永远返回 `{ success: true, noteId: undefined }`。我们不 fork 上游，在 wrapper 层追加回查。

E2E 验证已确认：回查创作者中心可以拿到真实 noteId（`verifiedVia: creator_center`），假成功被正确拦截为 `submitted_but_unverified`。

## Goals / Non-Goals

**Goals:**
- 消除假成功：发布后必须通过创作者中心回查确认 noteId，否则返回明确错误
- 两层防御：entrypoint 层回查 + opinion_mcp 层兜底
- 不改上游 npm 包，不 fork，不改 Dockerfile

**Non-Goals:**
- 修复上游 xhs-mcp 的 `publish.ts` 源码
- 处理新号首次发布被平台拦截的问题（需额外调查平台策略）
- 实现发布重试机制

## Decisions

### D1: 回查方式 — 创作者中心 API vs 全站搜索

**选择**: 创作者中心 `getMyPublishedNotes()`

**Alternatives**:
- 全站搜索 `search_feeds`: 超时风险高（Problem 9 已验证），且搜索结果不稳定
- 直接检查页面 URL 变化: 上游 bug 的根因就是这个方法不可靠

**Rationale**: 创作者中心是确定性 API，返回自己的笔记列表，匹配准确。虽然需要额外 5s 等待 + ~15s 查询，但可靠性远高于其他方案。

### D2: 匹配策略 — 标题精确匹配 + 时间窗口

**选择**: `note.title === title` + 发布时间 3 分钟内

**Rationale**: 标题是发布时明确传入的，精确匹配误判率极低。时间窗口防止匹配到旧的同名笔记。

### D3: 未验证时不写 DB

**选择**: `submitted_but_unverified` 时跳过 `db.published.record()`

**Alternatives**:
- 写入 `status: 'draft'`: 语义不准确
- 新增 CHECK 约束值: 需要修改上游 DB schema

**Rationale**: 无法确认笔记是否真的发出，不应写入发布记录。避免脏数据。

### D4: opinion_mcp 防御层 — note_url 为空即判定失败

**选择**: 上游返回 `success: true` 但 `note_url` 为 null 时返回 `success: false`

**Rationale**: 即使 entrypoint 层回查失败（异常降级），opinion_mcp 层也能兜底。两层防御确保假成功不会透传到用户。

### D5: check_login_status 超时 30s → 60s

**选择**: 增大超时到 60s

**Rationale**: Docker 环境下 Playwright 浏览器启动慢，30s 不够导致误判未登录。E2E 测试中复现了此问题。

## Risks / Trade-offs

- **发布耗时增加 ~20s** → 可接受，可靠性优先。未来可通过缓存创作者中心页面优化
- **创作者中心查询可能超时** → 超时时降级为 `submitted_but_unverified`，不返回假成功
- **连续发布同标题笔记可能误匹配** → 3 分钟时间窗口 + 精确标题匹配已足够区分
- **上游更新可能改变行为** → 我们的回查是纯追加逻辑，不依赖上游返回值，兼容性好
- **account 参数传递问题** → 当前需要显式传 account 名才能找到账号，`_default` fallback 不工作。此问题超出本次 scope，记录为已知限制
