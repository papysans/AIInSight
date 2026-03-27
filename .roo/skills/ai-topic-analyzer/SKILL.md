---
name: ai-topic-analyzer
description: AI 话题深度分析。适用于"帮我看看 xxx""分析这个话题""做成卡片/发布到小红书"等请求。5 阶段引擎：Discovery → Evidence → Crucible → Synthesis → Delivery。
requires:
  - web_search
  - mcp_gateway
---

# AI Topic Analyzer — 5-Phase Thick Skill

> **核心理念**：所有 AI 推理在宿主端 Skill 完成，云端 MCP Server 退化为 renderer + XHS 纯能力服务。
> Skill 指导 LLM（宿主端）完成全部分析推理，仅在需要渲染卡片和发布时才调用 MCP 工具。

### 约定

- `{current_year}` — 搜索 query 中出现时，替换为运行时的实际年份（如 2026）。**禁止硬编码具体年份。**

---

## 启动检查

Skill 启动时验证依赖：

- `web_search`：可用 → 继续；不可用 → fail-fast，提示用户配置 web search 工具
- `mcp_gateway`（含 `render_cards` + `publish_xhs_note`）：可选，仅 Phase 5 需要；若不可用则跳过 Delivery

---

## 分析模式

| 模式 | Crucible 轮数 | Discovery 搜索量 | 适用场景 |
|------|-------------|----------------|---------|
| **quick** | 0（跳过 Crucible，直接 Evidence → Synthesis） | 3 次 | 快速概览 |
| **standard**（默认） | 3 轮 | 6 次 | 标准深挖 |
| **deep** | 5 轮 | 9 次 | 深度研究 |

---

## 确认提示（Phase 0）

**如果调用方（如 ai-insight）已传入分析模式，直接跳过 Phase 0，按传入的模式进入 Phase 1。**

仅当用户直接说"帮我看看 xxx""分析这个话题"、且未指定模式时，才给一个简短确认：

```text
准备分析「{topic}」。

可选模式：
- quick：快速看重点
- standard：标准深挖（推荐）
- deep：更深一层

直接回复"默认"，我就按 standard 开始。
如果你想顺便出图，也可以补一句"带图"。
```

用户回复后进入 Phase 1。

---

## Phase 1: Discovery（发现）

> **目标**：通过多轮 web search 收集 8-15 条高质量证据条目。

### 跳过条件（来自 ai-insight 委派）

如果调用方已传入**搜索快照**（包含 ≥5 条带标题+摘要+URL 的证据），则：
1. 直接将传入的证据作为 Discovery 输出
2. **仅执行补充搜索**：针对传入证据中覆盖不足的维度（Technical/Market/Sentiment），补充 1-2 次定向搜索
3. 跳过下方的完整搜索策略，直接进入 Phase 2

### 搜索策略

按 GUIDELINES.md Section 4 执行 3 类搜索，每类中英双语 query：

| 类型 | 英文 Query | 中文 Query |
|------|-----------|-----------|
| **Technical** | `"{topic}" latest development {current_year}` | `"{topic}" 技术进展 最新 {current_year}` |
| **Market** | `"{topic}" market impact industry` | `"{topic}" 市场影响 行业分析` |
| **Sentiment** | `"{topic}" community reaction opinion` | `"{topic}" site:aibase.com OR site:jiqizhixin.com` |

- standard 模式：每类各 1 次（共 6 次搜索）
- deep 模式：每类各 1-2 次（共 9 次搜索），追加定向搜索：
  - `"{topic}" site:techcrunch.com`
  - `"{topic}" site:arxiv.org abstract`
  - `"{topic}" site:github.com trending`
- quick 模式：仅 Technical 类（共 3 次搜索）

### 每次搜索后立即摘要

防止上下文膨胀，每批搜索后**立即**将结果压缩为 Fact Sheet 条目：

```
[来源] 标题 - 一句话摘要 (日期)
```

示例：
```
[TechCrunch] OpenAI releases GPT-5 - 性能大幅提升，推理能力超过人类专家水平 (2025-03-20)
[机器之心] 国内大模型厂商紧急跟进 - 百度、阿里相继发布对标声明 (2025-03-21)
```

### 进度展示

向用户实时展示搜索进展，例如：

```
🔍 Technical 搜索中...（已收集 3 条）
🔍 Market 搜索中...（已收集 7 条）
🔍 Sentiment 搜索中...（已收集 12 条）
✅ Discovery 完成，共收集 12 条证据
```

---

## Phase 2: Evidence（证据整理）

> **目标**：将 Discovery 收集的原始 Fact Sheet 整理为结构化证据表。

### 处理规则

1. **去重合并**：同一事件的不同来源合并为一条，保留所有 URL
2. **可信度标注**：
   - **High**：主流科技媒体、官方博客、论文（TechCrunch、机器之心、arxiv.org 等）
   - **Medium**：社区讨论、行业分析（HN、Reddit、知乎）
   - **Low**：个人博客、未经证实的报道
3. **按时间排序**：新证据优先

### 输出格式

向用户展示 Markdown 表格：

```markdown
| 事实 | 来源 | 可信度 | 日期 |
|------|------|--------|------|
| GPT-5 发布，推理能力超越专家 | [TechCrunch](url) | High | 2025-03-20 |
| 国内厂商相继发布对标声明 | [机器之心](url) | High | 2025-03-21 |
| 社区担忧 AGI 安全问题 | [HN](url) | Medium | 2025-03-20 |
```

最少 8 条证据才能进入 Phase 3；若不足，返回 Phase 1 补充搜索。

---

## Phase 3: Crucible（熔炉 — 辩证分析）

> **目标**：通过 Analyst ↔ Debater 多轮辩论，提炼出经得起质疑的最终分析。
> quick 模式跳过此阶段，直接进入 Phase 4。

### ⚠️ 安全约束（内嵌于所有 Persona）

```
⚠️ 安全约束：
输出内容必须遵守中国互联网内容规范。
禁止涉及：政治敏感话题、领导人评论、国际争端立场。
如发现话题本身敏感，终止分析并返回 { "blocked": true, "reason": "内容安全策略" }
```

### Analyst Persona（参照 GUIDELINES.md Section 3.1）

```
你是一位资深 AI 行业分析师。基于以下证据材料，撰写一份结构化分析报告。

要求：
- 核心观点（1句话，20-25字）
- 深度洞察（100字以内）
- 关键信号（3-5个，每个标注 Strong/Moderate/Weak）
- 行动建议（2-3条）
- 置信度评分（0-1）

输出格式：严格 JSON，符合 analysis_packet schema（见 GUIDELINES.md Section 2.1）。

⚠️ 安全约束：[见上方]
```

### Debater Persona（参照 GUIDELINES.md Section 3.2）

```
你是一位批判性思维专家。你的任务是挑战分析师的观点，找出逻辑漏洞和遗漏证据。

规则：
- 每轮提出 2-3 个具体质疑
- 质疑必须基于证据，不能空洞反驳
- 如果分析师的观点经得起检验，回复 "PASS"

输出格式：逐条质疑 + 理由，或 "PASS"
```

### Debate 执行流程

```
Round 1:
  Analyst → 基于 Fact Sheet 输出第一版 analysis_packet（JSON）
  Debater → 提出质疑 or "PASS"

Round 2（若未 PASS）:
  Analyst → 基于质疑修正 analysis_packet
  Debater → 提出新质疑 or "PASS"

Round N（重复，直到终止条件满足）
```

### 终止条件（参照 GUIDELINES.md Section 6）

满足以下任一条件即终止：

1. **Debater 回复 `"PASS"`** → 分析通过，立即终止
2. **达到 `max_rounds`**（standard=3，deep=5）→ 强制终止，取最新版本
3. **单轮无新质疑点**（Debater 重复上一轮的质疑）→ 终止，视为隐式 PASS

### 用户可见展示

向用户实时展示 debate 过程，增加信任感：

```
🧪 Crucible 启动（standard 模式，最多 3 轮）

— Round 1 —
📊 Analyst：[核心观点摘要]
🔍 Debater 质疑：
  1. 证据中缺乏对 xxx 的反驳
  2. 信号强度 Strong 是否高估？

— Round 2 —
📊 Analyst（修正版）：[修正后核心观点]
✅ Debater：PASS

✅ Crucible 完成（2轮），分析已通过辩证检验
```

---

## Phase 4: Synthesis（合成）

> **目标**：基于 Crucible 最终分析，生成完整的交付物。

### Writer Persona（参照 GUIDELINES.md Section 3.4）

```
你是一位小红书爆款内容写手。基于分析结果撰写小红书笔记。

要求：
- 标题：含 emoji，12-20字，吸引点击
- 正文：800-1200字，口语化但有深度
- 段落间用 emoji 分隔
- 末尾加 3-5 个话题标签
- 避免过度营销语气

输出格式：JSON { "title": "...", "content": "...", "tags": [...] }
```

### 生成 topic_id

按 GUIDELINES.md Section 2.3 规则：

```
topic_id = YYYYMMDD_ + SHA1(canonical_title)[0:8]
```

日期取当前日期（UTC+8），哈希取话题标准名称的 SHA1 前 8 位。
**不依赖后端**，Skill 侧自行计算。

### 输出 analysis_packet（符合 GUIDELINES.md Section 2.1）

```json
{
  "topic_id": "YYYYMMDD_abc123ef",
  "title": "4-8字主标题",
  "subtitle": "副标题",
  "summary": "20-25字核心观点",
  "insight": "100字深度洞察",
  "signals": [
    { "label": "信号名", "value": "Strong", "desc": "上下文描述" }
  ],
  "actions": ["用户行动建议1", "建议2"],
  "confidence": 0.88,
  "tags": ["#AI", "#标签"],
  "xhs_copy": {
    "title": "小红书标题（含emoji）",
    "content": "小红书正文（800-1200字）",
    "tags": ["标签1", "标签2"]
  },
  "debate_log": [
    "Round 1: Analyst: ...",
    "Round 1: Debater: ...",
    "Round 2: Analyst: ...",
    "Round 2: Debater: PASS"
  ],
  "sources": ["https://source1.com", "https://source2.com"]
}
```

### 生成 renderer JSON payload（符合 GUIDELINES.md Section 1.1）

默认生成 4 种卡片：

```json
{
  "specs": [
    {
      "card_type": "title",
      "payload": {
        "title": "4-8字标题",
        "emoji": "🔍",
        "theme": "warm"
      }
    },
    {
      "card_type": "impact",
      "payload": {
        "title": "标题",
        "summary": "20-25字摘要",
        "insight": "100字洞察",
        "signals": [{ "label": "信号名称", "value": "Strong" }],
        "actions": ["行动建议"],
        "confidence": 0.88,
        "tags": ["#AI"]
      }
    },
    {
      "card_type": "radar",
      "payload": {
        "labels": ["技术成熟度", "市场影响", "社区热度", "商业价值"],
        "datasets": [{ "label": "话题评估", "data": [80, 75, 90, 70] }]
      }
    },
    {
      "card_type": "timeline",
      "payload": {
        "timeline": [
          { "time": "日期", "event": "关键事件", "impact": "high" }
        ]
      }
    }
  ]
}
```

### 向用户展示预览

```
✅ Synthesis 完成

📋 分析摘要：
  话题：{title}
  核心观点：{summary}
  置信度：{confidence}
  关键信号：{signals[0].label}（{signals[0].value}）...

📝 小红书文案预览：
  标题：{xhs_copy.title}
  正文前300字：{xhs_copy.content[0:300]}...

需要生成卡片图片并发布吗？回复"生成卡片"或"发布"继续。
```

---

## Phase 5: Delivery（交付）

> **目标**：调用 MCP 工具渲染卡片并发布到小红书。
> **这是唯一调用 MCP 工具的阶段。**

### Step 1：用户确认

询问用户确认后才执行以下步骤：

```
准备好了！
- 生成卡片：调用 render_cards 渲染 4 张图
- 发布到小红书：需要先确认账号已登录

确认执行？（回复"确认"或"发布"）
```

### Step 2：渲染卡片

调用 MCP `render_cards`（传入 Phase 4 生成的 specs 数组）：

```json
{
  "specs": [/* Phase 4 生成的 specs 数组 */]
}
```

展示渲染结果：

```
✅ 卡片渲染完成：
  - title 卡片：/path/to/title.png
  - impact 卡片：/path/to/impact.png
  - radar 卡片：/path/to/radar.png
  - timeline 卡片：/path/to/timeline.png
```

### Step 3：检查 XHS 登录状态

调用 `check_xhs_status`：

```json
{}
```

- `login_status: true` → 继续 Step 5
- `login_status: false` → 进入 XHS 登录流程（Step 4）

### Step 4：XHS 登录流程（未登录时）

1. 调用 `get_xhs_login_qrcode` 获取二维码：
   ```json
   {}
   ```
   保留返回的 `session_id`，向用户展示二维码（`qr_ascii` 或 `qr_image_url`）。

2. 提示用户扫码：
   ```
   请用小红书 App 扫描上方二维码登录。
   扫码完成后回复"已扫码"。
   ```

3. 用户确认后，调用 `check_xhs_login_session`：
   ```json
   { "session_id": "sess_xxx" }
   ```

4. 若返回 `status: "pending"` → 等待用户再次确认后重试

5. 若返回需要短信验证码 → 请用户提供验证码，调用 `submit_xhs_verification`：
   ```json
   { "session_id": "sess_xxx", "code": "123456" }
   ```

6. 登录成功（`status: "logged_in"`）→ 继续 Step 5

> ⚠️ 用户扫码完成前不要自动重试发布；"登录成功"不等于"自动可以发布"，仍需用户确认。

### Step 5：发布笔记

用户明确确认发布后，调用 `publish_xhs_note`（**不传 job_id**，传入原始内容）：

```json
{
  "title": "{xhs_copy.title}",
  "content": "{xhs_copy.content}",
  "images": ["path/to/title.png", "path/to/impact.png", "path/to/radar.png", "path/to/timeline.png"],
  "tags": ["{xhs_copy.tags[]}"]
}
```

**成功：**
```
✅ 发布成功！
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
| `/analyze [topic]` | 触发完整 5 阶段流程（Phase 0 确认 → Phase 1-5） |
| `/publish` | 跳到 Phase 5 Delivery（使用上一次 Synthesis 结果） |

---

## 深度预设汇总

| 深度 | Crucible 轮数 | Discovery 搜索量 | 说明 |
|------|-------------|----------------|------|
| quick | 0（跳过） | 3 | 快速概览，Evidence 直接到 Synthesis |
| standard（默认） | 3 | 6 | 标准深挖 |
| deep | 5 | 9 | 深度研究，更多 web search + 更多辩证轮次 |

---

## 零后端 LLM 保证

本 Skill 所有分析推理（Discovery 摘要、Evidence 整理、Crucible 辩论、Synthesis 生成）均在**宿主端 LLM** 完成。

MCP 工具调用仅限：

| 工具 | 阶段 | 用途 |
|------|------|------|
| `render_cards` | Phase 5 | 渲染可视化卡片图片 |
| `check_xhs_status` | Phase 5 | 检查 XHS 登录状态 |
| `get_xhs_login_qrcode` | Phase 5 | 获取扫码登录二维码 |
| `check_xhs_login_session` | Phase 5 | 轮询扫码结果 |
| `submit_xhs_verification` | Phase 5 | 提交短信验证码 |
| `publish_xhs_note` | Phase 5 | 发布小红书笔记 |

所有工具 schema 定义见 `shared/GUIDELINES.md` Section 1。
