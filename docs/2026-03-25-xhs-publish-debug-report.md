# 2026-03-25 小红书发布链路排障文档（含详细日志）

## 文档目的

这份文档记录本次会话中，小红书图文渲染与发布链路暴露出的**全部关键问题**，并附上：

- 复现过程
- 准确根因
- 关键日志
- 当前结论
- 建议修复方向

这份文档偏技术排障视角，适合直接转给另一边定位和修复。

---

## 一、总体结论

本次链路暴露的问题，不是单点故障，而是多个阶段连续掉坑：

1. **简单出图任务流程过重**，用户体验差
2. **发布账号与登录账号不一致**，导致首次发布失败
3. **二维码展示不稳定**，用户容易错过扫码
4. **图片路径跨容器不可见**，导致 `No valid image files found`
5. **impact 卡片 payload 契约不清晰**，首次渲染失败
6. **发布成功判定过早**：日志显示 `Publish successful`，数据库 `published_notes` 也有记录，但 `note_id` 为空，`my_published_notes` 为空，用户前台不可见

最重要的新问题是第 6 条：

> 当前链路把“浏览器点了发布且未报错”当成“最终发帖成功”，但实际上没有拿到 `note_id`，也没有回查到用户的已发布内容，因此成功判定不可靠。

---

## 二、问题清单

### 问题 1：简单出图任务前置确认过多，流程偏重

#### 用户表现

用户明确说“帮我渲染小红书的图片”，但系统没有直接出图，而是走了多轮：

- visual companion 提示
- 图片类型确认
- A/B/C 方案确认
- 设计确认
- 计划与说明

#### 问题判断

这不是信息不足，而是对操作型任务误用了重设计流程。

#### 建议

- 对“渲染图片/出图/做卡片”类操作型任务走 fast path
- 默认直接用仓库现成组合：`title + daily-rank` 或单话题 `title + impact + radar + timeline`
- 先出图，再问用户要不要改

---

### 问题 2：首次发布时账号上下文错乱，报 `Account not found: _default`

#### 现象

系统先判断“已登录”，但发布时报：

```text
Account not found: _default
```

#### 根因

- 检查登录态时没严格绑定目标 `account_id`
- 发布时落回 `_default`
- `xhs-mcp` 多账号模式要求“登录 / 检查 / 发布”必须全程同一个账号 ID

#### 关键日志

首次失败前后，系统内部实际已经暴露了“账号错用”问题：

```text
Account not found: _default
```

以及后续重新排查中，明确发现：

- 原账号 ID：`b5510c64-87b8-482e-a537-2621388d4313`
- 旧账号昵称：`小红薯6975F30A`

#### 修复建议

- `get_xhs_login_qrcode(account_id=...)`
- `check_xhs_login_session(session_id, account_id=...)`
- `check_xhs_status(account_id=...)`
- `publish_xhs_note(..., account_id=...)`

必须形成闭环，禁止任何环节自动回退 `_default`。

---

### 问题 3：二维码展示不稳定，ASCII 失败

#### 现象

用户反馈“刚刚没看到二维码”，需要反复重新生成。

#### 根因

ASCII 二维码生成依赖缺失：

```text
[XHS QR] ASCII QR 生成依赖缺失: No module named 'PIL'
```

导致只能依赖外链图片展示二维码，用户很容易错过。

#### 关键日志

```text
2026-03-25 19:44:29.596 | WARNING  | opinion_mcp.services.xiaohongshu_publisher:_generate_ascii_qr:311 - [XHS QR] ASCII QR 生成依赖缺失: No module named 'PIL'
```

#### 修复建议

- 修复 `_generate_ascii_qr` 依赖
- 即使 ASCII 失败，也统一以结构化方式输出：
  - 二维码链接
  - session_id
  - 过期时间
  - 操作提示

---

### 问题 4：首次榜单发布失败，图片路径跨容器不可见

#### 现象

登录成功后第一次真正发布榜单时，报：

```text
No valid image files found
```

#### 根因

传给发布器的是 `mcp` 容器里的路径：

```text
/app/outputs/card_previews/_default/...
```

但 `xhs-mcp` 实际只能访问共享卷路径：

```text
/app/images/...
```

#### 关键日志

```text
2026-03-25T11:09:27.702Z [WARN] [browser] Image file not found {"path":"/app/outputs/card_previews/_default/20260325_185217_title_b4209cea.png"}
2026-03-25T11:09:27.702Z [WARN] [browser] Image file not found {"path":"/app/outputs/card_previews/_default/20260325_185218_daily_rank_d42c6679.png"}
2026-03-25T11:09:27.702Z [ERROR] [browser] No valid image paths
```

#### 已验证可行的修法

这次会话里已经证明可行：

- 把图片转成 `data:image/png;base64,...`
- 交给 `_process_image()`
- 让它写入共享卷：`/app/runtime/xhs/images/...`
- 最终映射成 `xhs-mcp` 可见路径：`/app/images/...`

#### 修复建议

- 上层调用方不应该关心容器路径
- `publish_xhs_note()` / `_process_image()` 应自动兼容：
  - 本地路径
  - HTTP URL
  - data URL

---

### 问题 5：`impact` 卡片首次渲染失败，payload 契约不够清晰

#### 现象

单话题 `Sora` 图文卡片渲染时，`title/radar/timeline` 成功，但 `impact` 失败。

#### 错误日志

```text
[CardRenderClient] HTTP 500: {"success":false,"error":"page.evaluate: TypeError: (i || \"\").trim is not a function ..."}
```

renderer 日志：

```text
[renderer] Error rendering impact: page.evaluate: TypeError: (i || "").trim is not a function
```

#### 根因

首次给 `impact` 卡传的是对象数组：

```json
"signals": [
  {"label": "产品路线", "value": "Strong"}
]
```

但实际前端渲染器期待的是**字符串数组**，内部直接对每一项执行 `.trim()`。

#### 已验证的正确格式

下面这个 payload 已经验证能成功渲染：

```json
"signals": ["产品路线收缩", "成本压力高", "市场进入调整"]
```

#### 关键验证日志

```text
{"results": [{"success": true, "output_path": "/app/outputs/card_previews/_default/20260325_193646_impact_b746853c.png", "image_url": null, "card_type": "impact"}]}
```

#### 修复建议

- 明确 renderer schema 文档
- `impact` 的 `signals/actions/confidence` 字段约束需要写入技能和接口文档
- 最好在 API 层加 schema 验证，不要让前端运行时才炸

---

### 问题 6：登录成功后重新扫码，实际创建了新账号实体

#### 现象

用户说原账号被 ban，要求重新扫码。扫码后系统新建了一个账号，而不是复用旧账号。

#### 实际结果

新扫码生成的账号是：

- 昵称：`小红薯6976CA3D`
- account_id：`722d4509-26c3-4424-98c9-1879035ebbcc`
- redId：`63508144097`

#### 关键日志

```text
{"success": true, "status": "logged_in", "message": "{\n  \"success\": true,\n  \"status\": \"success\",\n  \"account\": {\n    \"id\": \"722d4509-26c3-4424-98c9-1879035ebbcc\",\n    \"name\": \"小红薯6976CA3D\",\n    \"status\": \"active\"\n  }, ... }"}
```

以及 `xhs-mcp` 登录日志：

```text
2026-03-25T11:45:20.191Z [login-session] Login successful {"sessionId":"sess_vntaf0p4","userId":"69761f53000000002102f9f6"}
```

#### 风险

- 用户以为是在原账号里重新登录，实际上系统内部可能新建了一个账号实体
- 若上层不明确展示当前 account_id / nickname，用户会误判“为什么我看不到”

#### 修复建议

- 扫码成功后必须明确向用户展示：
  - 当前登录账号昵称
  - 当前 account_id
  - 是否为新账号实体
- 如果是“切号”而非“续登”，要明确提示

---

### 问题 7：Sora 图文发布显示成功，但前台可见性无法确认

#### 现象

系统显示：

```json
{"success": true, "note_url": null}
```

同时用户在前台看不到该内容。

#### 关键日志（自动化层）

第二次换号后，`xhs-mcp` 浏览器自动化完整记录为：

```text
2026-03-25T11:45:51.119Z [INFO] [browser] Starting publishContent {"title":"🎬OpenAI关停Sora说明了什么？","imageCount":4}
2026-03-25T11:46:08.240Z [INFO] [browser] Uploading images {"count":4}
2026-03-25T11:46:10.286Z [INFO] [browser] All images uploaded {"count":4}
2026-03-25T11:46:12.306Z [INFO] [browser] Title set {"title":"🎬OpenAI关停Sora说明了什么？"}
2026-03-25T11:46:13.168Z [INFO] [browser] Content set (via textbox)
2026-03-25T11:46:20.635Z [INFO] [browser] Tags added
2026-03-25T11:46:20.635Z [INFO] [browser] Clicking publish button...
2026-03-25T11:46:20.693Z [INFO] [browser] Publish button clicked
2026-03-25T11:46:23.694Z [INFO] [browser] Publish successful {}
```

#### 关键数据库证据

`xhs-mcp` SQLite 中，`published_notes` 确实新增记录：

```json
{
  "id": 4,
  "account_id": "722d4509-26c3-4424-98c9-1879035ebbcc",
  "note_id": null,
  "title": "🎬OpenAI关停Sora说明了什么？",
  "status": "published",
  "published_at": "2026-03-25T11:46:25.704Z"
}
```

但同时存在两个关键异常：

1. `note_id` 为 `null`
2. `my_published_notes` 表为空：

```json
MY_PUBLISHED_NOTES_ROWS=[]
```

#### 准确判断

这说明当前系统把下面这个条件当成了“成功”：

- 浏览器点击发布按钮后没有立刻报错
- sidecar 本地写入了一条 `published_notes` 记录

但这并不等于：

- 平台前台已可见
- 已拿到正式 noteId
- 已同步到“我的发布内容”视图

也就是说，现在的“发布成功”判定**过早**。

#### 最可能的真实状态

目前更合理的判断是：

- 自动化提交流程已完成
- sidecar 本地标记为了 `published`
- 但平台最终结果未回传，或 sidecar 未成功抓取最终帖子 ID

因此用户前台看不到，并不矛盾。

#### 修复建议（最关键）

发布成功条件必须升级，至少满足其一才允许返回 success：

1. 拿到 `note_id`
2. 构造出可访问 `note_url`
3. 成功回查到 `my_published_notes` 中对应标题/内容

如果都没有，返回值必须改成：

```json
{
  "success": false,
  "status": "submitted_but_unverified",
  "message": "发布动作已提交，但未能确认前台帖子已生成"
}
```

而不能继续返回：

```json
{"success": true, "note_url": null}
```

#### 优先级

P0。这是当前发布链路里最严重的“假成功”问题。

---

### 问题 8：`published_notes` 与 `my_published_notes` 状态不一致

#### 现象

数据库显示：

- `published_notes` 有记录
- `my_published_notes` 为空

#### 关键证据

```json
PUBLISHED_NOTES_ROWS=[
  {
    "id":4,
    "account_id":"722d4509-26c3-4424-98c9-1879035ebbcc",
    "note_id":null,
    "title":"🎬OpenAI关停Sora说明了什么？",
    "status":"published"
  }
]

MY_PUBLISHED_NOTES_ROWS=[]
```

#### 判断

这说明 sidecar 内部至少有两套“发布后状态源”：

- 一套是发布流程自己写入 `published_notes`
- 一套是“我的已发布内容”同步到 `my_published_notes`

但这两套没有闭环校验。

#### 修复建议

- `published_notes` 不应直接作为最终成功依据
- 发布后必须追加一次“我的内容列表”回查
- 如果 `my_published_notes` 没同步到，状态应为 `pending_verification` 而不是 `published`

---

### 问题 9：搜索回查能力不足，无法可靠验证新发笔记

#### 现象

尝试通过 `search_feeds` 搜索标题回查时，直接超时：

```text
2026-03-25 19:48:28.124 | INFO     | opinion_mcp.services.xiaohongshu_publisher:_call_mcp:373 - [XHS MCP] Calling tool: search_feeds → xhs_search
2026-03-25 19:48:58.167 | ERROR    | opinion_mcp.services.xiaohongshu_publisher:_call_mcp:454 - [XHS MCP] Timeout:
{"success": false, "error": "请求超时，请稍后重试"}
```

#### 影响

- 无法用搜索结果做 post-publish 验证
- 用户前台看不到时，系统无法进一步确认到底是未发布、审核中还是已发但未同步

#### 修复建议

- 优先做 `my_published_notes` 回查，而不是全站搜索
- 若必须搜索，增加超时和关键字退化策略
- 最好暴露一个“获取最近发布笔记”的专用能力，而不是依赖搜索

---

## 三、建议优先级

### P0

1. **发布成功判定过早**：`note_id` 为空仍返回 success
2. **发布后缺少回查闭环**：未验证 `my_published_notes` 或前台帖子存在
3. **多账号链路必须全程绑定 account_id**，禁止回退 `_default`
4. **图片路径必须自动标准化到共享卷**

### P1

5. `impact` 卡片 schema 明确化与接口校验
6. 二维码 ASCII 依赖修复
7. 切号后必须明确提示“当前实际发布账号”

### P2

8. 搜索回查增强
9. 简单操作任务的 fast path 优化

---

## 四、建议给另一边的短结论

可以直接转这段：

```text
这次最严重的问题不是单纯“发布失败”，而是“发布成功判定过早”。

目前链路里，xhs-mcp 只要完成了：上传图片、填写标题正文、点击发布按钮，并且浏览器端没立即报错，就会记日志 `Publish successful {}`，并在 `published_notes` 表里写一条 `status='published'` 记录。

但这次复查发现：
1. 该记录的 `note_id` 是 null
2. `my_published_notes` 表是空的
3. 用户在前台看不到内容

也就是说，现在系统把“提交发布动作成功”误判成了“前台发帖成功”。

建议立刻修改成功条件：至少拿到 `note_id`、或构造出 `note_url`、或回查到 `my_published_notes` 之一，才允许返回 success。否则应该返回 `submitted_but_unverified`，不能再返回 `success: true, note_url: null`。

同时，本次还验证了另外几个问题：
- 多账号上下文曾导致 `_default` 账号错误
- 图片路径跨容器不可见导致 `No valid image files found`
- impact 卡片实际要求 `signals` 为字符串数组，schema 文档不清
- 二维码 ASCII 生成功能依赖缺失
```

---

## 五、结论

本次最关键的新发现是：

> **当前发布链路存在“假成功”风险。**

自动化、日志、sidecar 本地数据库都可能说“成功”，但用户前台仍然看不到，因为系统没有把“平台最终成帖确认”纳入成功条件。

这是需要优先修复的核心问题。
