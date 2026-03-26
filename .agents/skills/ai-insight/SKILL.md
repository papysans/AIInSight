---
name: ai-insight
description: AI 日报助手 - 通过 web search 采集 AI 领域热点，评分排名后生成日报榜单。用户选题后转入 ai-topic-analyzer 进行深度分析。适用于"今日AI热点""AI日报""今天有什么AI新闻"等请求。
requires:
  - web_search
  - mcp_gateway
---

# AI Insight — 4-Phase Daily Report Pipeline

> **核心理念**：所有 AI 推理在宿主端 Skill 完成，云端 MCP Server 退化为 renderer + XHS 纯能力服务。
> ai-insight 负责日报采集、评分、排名；用户选题后委托给 ai-topic-analyzer 完成深度分析。

---

## 启动检查

Skill 启动时验证依赖：

- `web_search`：可用 → 继续；不可用 → fail-fast，提示用户配置 web search 工具
- `mcp_gateway`（含 `render_cards` + `publish_xhs_note`）：可选，仅榜单发布时需要；若不可用则跳过 Delivery

---

## 触发条件

用户发送以下任意内容时，**进入 Phase 1**：

- "今日AI有什么热点"
- "AI日报"
- "今天有什么AI新闻"
- "AI今天发生了什么"
- `/ai-daily`

> ⚠️ 触发时**不要立刻深度分析任何单一话题**，先走完 Phase 1-3 展示榜单，等待用户选题。

---

## 直接渲染触发（Fast Path）

用户发送以下内容时，**跳过 Phase 1-3，直接进入榜单卡片流程 Step 1**：

- "帮我渲染小红书图片" / "出图" / "渲染图片" / "做卡片"
- "发布榜单" / `/publish-today`
- "帮我发" / "发了吧"

**前提**：当前会话中已有 `daily_topics[]` 数据（来自之前的 Phase 2）。

若无数据，提示："还没有今日热点数据，先执行 `/ai-daily` 采集一下？"

> ⚠️ 直接渲染时使用默认方案（title + daily-rank，theme=warm），**渲染完再问用户是否需要调整**，不在渲染前追问方案选择。

---

## Phase 1: Pulse（脉搏 — 热点采集）

> **目标**：执行 3-5 次定向 web search，采集 20-30 条原始 AI 新闻条目。
> **零 MCP 调用**，全部在宿主端完成。

### 搜索策略

按以下顺序执行（参照 GUIDELINES.md Section 4.3 日报额外定向搜索）：

| 轮次 | Query | 说明 |
|------|-------|------|
| 1 | `"today AI news" site:aibase.com` | AIbase 今日新闻 |
| 2 | `"今日AI" site:jiqizhixin.com OR site:qbitai.com` | 机器之心 / 量子位 |
| 3 | `"AI" site:techcrunch.com latest` | TechCrunch 最新 |
| 4 | `"AI breakthrough" OR "AI release" today 2025 OR 2026` | 突破性进展 |
| 5 | `"AI" site:github.com trending` | GitHub 热门 AI 项目 |

### 每次搜索后立即摘要

防止上下文膨胀，每次搜索后**立即**将结果压缩为条目格式（参照 GUIDELINES.md Section 4.2）：

```
[来源] 标题 - 一句话摘要 (日期)
```

示例：
```
[AIBase] GPT-5 发布 - OpenAI 发布 GPT-5，推理能力大幅提升 (2026-03-25)
[量子位] 国产大模型新突破 - 某厂商发布百亿参数开源模型，性能超越同量级 SOTA (2026-03-24)
[TechCrunch] Google DeepMind new paper - 提出新架构，训练效率提升 3× (2026-03-25)
```

### 进度展示

```
🔍 正在采集 AI 热点...

📡 搜索 aibase.com...（已收集 N 条）
📡 搜索 机器之心/量子位...（已收集 N 条）
📡 搜索 TechCrunch...（已收集 N 条）
📡 搜索突破性进展...（已收集 N 条）
📡 搜索 GitHub 热榜...（已收集 N 条）

✅ Pulse 完成，共采集 N 条原始条目，进入评分处理...
```

---

## Phase 2: Processing（处理 — 评分排名）

> **目标**：在宿主端 LLM 一次性完成去重、评分、聚类、排名，输出 Top 10 话题列表。
> **零 MCP 调用**，全部在宿主端完成。

### 处理步骤（LLM 一次性完成）

**Step 1：去重合并**

- 相同事件/话题的不同来源报道合并为一个话题
- 保留所有来源 URL，记录 source_count

**Step 2：评分（使用 Evaluator Persona，参照 GUIDELINES.md Section 3.3）**

对每个合并后的话题，在内部执行以下评分：

```
你是一位新闻评分专家。对以下 AI 新闻/话题进行评分。

评分维度（1-10分）：
- Novelty（新颖度）：是否为首次报道/突破性进展
- Impact（影响力）：对行业/用户的实际影响程度
- Credibility（可信度）：信源质量和交叉验证程度

输出格式：JSON { "novelty": N, "impact": N, "credibility": N, "total": N, "reasoning": "一句话理由" }

⚠️ 安全约束：
输出内容必须遵守中国互联网内容规范。
禁止涉及：政治敏感话题、领导人评论、国际争端立场。
如发现话题本身敏感，返回 { "blocked": true, "reason": "内容安全策略" }
```

total = (novelty × 0.3 + impact × 0.4 + credibility × 0.3)，保留一位小数。

**Step 3：聚类**

相关话题（同一产品/公司/技术方向）归入同一簇，避免榜单重复。

**Step 4：排名**

按 total 分数降序取 Top 10，生成 `daily_topics[]`（符合 GUIDELINES.md Section 2.2 schema）：

```json
{
  "canonical_title": "话题标准名称",
  "summary_zh": "一句话中文摘要",
  "tags": ["AI", "LLM"],
  "score_breakdown": {
    "novelty": 8,
    "impact": 9,
    "credibility": 7,
    "total": 8.3
  },
  "source_urls": ["https://..."],
  "topic_id": "20260325_hash8chars"
}
```

**Step 5：生成 topic_id（按 GUIDELINES.md Section 2.3）**

```
topic_id = YYYYMMDD_ + SHA1(canonical_title)[0:8]
```

日期取当前日期（UTC+8），哈希取 `canonical_title` 字符串的 SHA1 前 8 位。不依赖后端，Skill 侧自行生成。

---

## Phase 3: Selection（选择 — 展示与选题）

> **目标**：向用户展示 Top 10 榜单，等待用户选择下一步操作。
> **零 MCP 调用**，纯展示与等待用户输入。

### 展示格式

```
🤖 AI 日报 — {YYYY-MM-DD}

📊 Top 10 AI 热点:

1. 🔥 {话题标题} — {N}个来源 | 评分: {total} | #{tag1} #{tag2}
   {summary_zh}

2. 📈 {话题标题} — {N}个来源 | 评分: {total} | #{tag1}
   {summary_zh}

3. 🧪 {话题标题} — {N}个来源 | 评分: {total} | #{tag1}
   {summary_zh}

4-10. ...（同上格式）

━━━━━━━━━━━━━━━━━━━━━━
💬 接下来可以：
  • 回复话题编号进行深度分析（如"分析 1"或"1"）
  • 回复"发布榜单"生成榜单卡片并发布到小红书
  • 回复"分析全部"对 Top 3 依次深度分析
```

### 等待用户输入

| 用户输入 | 行为 |
|---------|------|
| 数字（如"1"、"分析 3"） | 进入 Phase 4，委托 ai-topic-analyzer 分析对应话题 |
| "发布榜单" / `/publish-today` | 进入榜单卡片流程 |
| "分析全部" | 对 Top 3 依次进入 Phase 4 |
| `/analyze [topic_or_id]` | 直接委托给 ai-topic-analyzer |

---

## Phase 4: Delegation（委托 — 转入深度分析）

> **目标**：将用户选择的话题委托给 **ai-topic-analyzer 的 Phase 1-5 流程**，传递已有证据避免重复搜索。
> **不重复实现**深度分析逻辑。

### 委托流程

**Step 1：确认话题与深度**

从 `daily_topics[]` 中找到用户选择的话题（按编号或 topic_id），向用户确认：

```
准备深度分析「{canonical_title}」。

可选模式：
- quick：快速看重点
- standard：标准深挖（推荐）
- deep：更深一层

直接回复"默认"按 standard 开始。
如果你想顺便出图，也可以补一句"带图"。
```

**Step 2：传递已有上下文**

用户确认后，转入 **ai-topic-analyzer**，传递以下初始上下文（让 ai-topic-analyzer 可跳过或精简 Phase 1 Discovery 的重复搜索）：

```
话题：{canonical_title}
已有证据摘要（来自日报采集）：
{source_urls 中每条来源的摘要条目，格式：[来源] 标题 - 摘要 (日期)}

请从 Phase 2 Evidence 整理开始；如需补充专项搜索以提升分析深度，可执行追加搜索。
```

**Step 3：ai-topic-analyzer 完成全流程**

ai-topic-analyzer 完成 Discovery → Evidence → Crucible → Synthesis → Delivery 五阶段流程。

> ⚠️ Phase 4 **不重复实现**任何分析逻辑，完全委托给 ai-topic-analyzer SKILL.md 定义的流程。

---

## 榜单卡片流程（`/publish-today` 或"发布榜单"）

> 当用户要求"把今天的榜单做成小红书图文"或"发布榜单"时执行。

### Step 1：构造 daily-rank renderer payload

基于 Phase 2 生成的 `daily_topics[]`，构造（符合 GUIDELINES.md Section 1.1）：

```json
{
  "specs": [
    {
      "card_type": "title",
      "payload": {
        "title": "AI 今日热点",
        "emoji": "🤖",
        "theme": "warm"
      }
    },
    {
      "card_type": "daily-rank",
      "payload": {
        "date": "{YYYY-MM-DD}",
        "title": "AI 每日热点",
        "topics": [
          { "rank": 1, "title": "{canonical_title}", "score": 9.0, "tags": ["{tag1}", "{tag2}"] },
          { "rank": 2, "title": "{canonical_title}", "score": 8.8, "tags": ["{tag1}"] }
        ]
      }
    }
  ]
}
```

### Step 2：渲染卡片

调用 MCP `render_cards`（传入上方 specs）：

```json
{
  "specs": [/* 上方构造的 specs */]
}
```

展示渲染结果：
```
✅ 榜单卡片渲染完成：
  - title 卡片：/path/to/title.png
  - daily-rank 卡片：/path/to/daily-rank.png
```

### Step 3：用户确认发布

```
以上是今日 AI 热点榜单卡片预览。
确认发布到小红书？（回复"确认发布"）
```

> ⚠️ 必须获得用户明确确认，不能自动发布。

### Step 4：构造小红书文案

用户确认后，在宿主端 LLM 生成发布文案（使用 Writer Persona，参照 GUIDELINES.md Section 3.4）：

- 标题：含 emoji，12-20字，吸引点击
- 正文：500-800字，口语化，突出 Top 3 话题亮点
- 末尾加 3-5 个话题标签

### Step 5：检查 XHS 登录状态

调用 `check_xhs_status`：
- `login_status: true` → 继续 Step 6
- `login_status: false` → 进入 XHS 登录流程：
  1. 调用 `get_xhs_login_qrcode` → 展示 `qr_ascii`（终端直接扫码），保留 `session_id`
  2. 提示用户扫码后回复"已扫码"
  3. 调用 `check_xhs_login_session` 轮询状态（传入 `session_id`）
  4. 若返回需要验证码 → 请用户提供，调用 `submit_xhs_verification`（传入 `session_id` + `code`）
  5. `status: "logged_in"` → 继续 Step 6

> ⚠️ 用户扫码完成前不要自动重试；"登录成功"不等于"自动发布"，仍需用户确认。

### Step 6：发布笔记

调用 `publish_xhs_note`（传入原始内容，不传 job_id）：

```json
{
  "title": "{xhs_title}",
  "content": "{xhs_content}",
  "images": ["path/to/title.png", "path/to/daily-rank.png"],
  "tags": ["{tag1}", "{tag2}", "AI日报", "AI热点"]
}
```

**成功：**
```
✅ 今日 AI 日报发布成功！
  笔记链接：https://www.xiaohongshu.com/...
```

**失败：**
```
❌ 发布失败：{error}
不要自动重试，请用户决定下一步。
```

> ⚠️ 发布失败时**不要自动重试**，等待用户指令。

---

## 命令语义

| 命令 | 行为 |
|------|------|
| `/ai-daily` | 触发完整 Phase 1-3 流程（采集 → 评分 → 展示榜单） |
| `/analyze [topic_or_id]` | 跳到 Phase 4，委托给 ai-topic-analyzer 深度分析 |
| `/publish [topic_or_id]` | 对选定话题走 ai-topic-analyzer Phase 5 Delivery |
| `/publish-today` | 榜单卡片流程（render_cards + publish_xhs_note） |

---

## MCP 工具调用时机

> Phase 1-3 **零 MCP 调用**，全部在宿主端 LLM 完成。

| 工具 | 调用时机 | 用途 |
|------|---------|------|
| `render_cards` | 榜单卡片流程 Step 2 | 渲染 title + daily-rank 卡片图片 |
| `publish_xhs_note` | 榜单卡片流程 Step 6 | 发布小红书笔记 |
| `check_xhs_status` | 榜单卡片流程 Step 5 | 检查 XHS 登录状态 |
| `get_xhs_login_qrcode` | XHS 登录流程 | 获取扫码登录二维码 |
| `check_xhs_login_session` | XHS 登录流程 | 轮询扫码结果 |
| `submit_xhs_verification` | XHS 登录流程 | 提交短信验证码 |

所有工具 schema 定义见 `shared/GUIDELINES.md` Section 1。

---

## 安全约束（参照 GUIDELINES.md Section 7）

所有内容生成步骤（评分摘要、文案生成）均内嵌以下安全约束：

```
⚠️ 安全约束：
输出内容必须遵守中国互联网内容规范。
禁止涉及：政治敏感话题、领导人评论、国际争端立场。
如发现话题本身敏感，终止处理并返回 { "blocked": true, "reason": "内容安全策略" }
```

MCP 端 `publish_xhs_note` 调用前，server 端还会执行 preflight 内容安全检查（第二道防线，参照 GUIDELINES.md Section 7.2）。

---

## 零后端 LLM 保证

本 Skill 所有分析推理（Pulse 摘要、Processing 评分排名聚类、Selection 展示、Delegation 话题传递、文案生成）均在**宿主端 LLM** 完成。

ai-topic-analyzer 的深度分析同样在宿主端完成（见 `.agents/skills/ai-topic-analyzer/SKILL.md`）。

MCP 工具调用仅限榜单渲染与 XHS 发布，详见上方"MCP 工具调用时机"表格。
