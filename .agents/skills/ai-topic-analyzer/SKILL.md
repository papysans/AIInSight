---
name: ai-topic-analyzer
description: AI 话题深度分析。适用于"帮我看看 xxx""分析这个话题""做成卡片/发布到小红书"等请求。5 阶段引擎：Discovery → Evidence → Deep Search → Smart Synthesis → Delivery。
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

| 模式 | Deep Search 搜索量 | Discovery 搜索量 | 适用场景 |
|------|-------------------|----------------|---------|
| **quick** | 0（跳过 Deep Search，Evidence → Smart Synthesis） | 3 次 | 快速概览 |
| **standard**（默认） | 3-5 次（中文源优先） | 6 次 | 标准深挖 |
| **deep** | 6-9 次（覆盖所有数据源） | 9 次 | 深度研究 |

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

最少 8 条证据才能进入 Phase 2.5；若不足，返回 Phase 1 补充搜索。

---

## Phase 2.5: Deep Search（深度检索）

> **目标**：针对热点从垂直数据源深度检索，补充高质量证据。
> quick 模式跳过此阶段，直接进入 Phase 3。

### 垂直数据源列表

| 类型 | 数据源 | 搜索语法 |
|------|--------|---------|
| **中文 AI 媒体** | AIBase | `"{topic}" site:aibase.com` |
| | 机器之心 | `"{topic}" site:jiqizhixin.com` |
| | 量子位 | `"{topic}" site:qbitai.com` |
| **英文技术源** | TechCrunch | `"{topic}" site:techcrunch.com` |
| | arXiv | `"{topic}" site:arxiv.org abstract {current_year}` |
| | GitHub | `"{topic}" site:github.com trending` |

### 执行策略

- **standard 模式**：执行 3-5 次定向搜索（中文源优先）
- **deep 模式**：执行 6-9 次定向搜索（覆盖所有数据源）
- **quick 模式**：跳过此阶段

### Rate Limit 降级

deep 模式下，若连续 2 次搜索返回错误（超时、rate limit、空结果），自动降级：

1. 将剩余 Deep Search 搜索量上限降为 3 次（standard 模式水平）
2. 向用户展示降级通知
3. **不重试**已失败的查询，继续执行剩余搜索

### 去重合并

Deep Search 结果与 Phase 2 的 fact_sheet 合并时：

1. **按 URL 去重**：相同 URL 跳过
2. **按事件合并**：相同事件的不同来源合并为一条，保留所有 URL
3. **保持时间排序**：新证据插入到对应时间位置

### 进度展示

```
🔎 Deep Search 启动（standard 模式）

🔎 搜索 AIBase...（已补充 2 条）
🔎 搜索机器之心...（已补充 4 条）
🔎 搜索 TechCrunch...（已补充 6 条）

✅ Deep Search 完成，共补充 6 条高质量证据
```

Rate limit 降级时展示：

```
🔎 Deep Search 启动（deep 模式）

🔎 搜索 AIBase...（已补充 2 条）
🔎 搜索机器之心...（已补充 3 条）
🔎 搜索量子位...❌ 搜索失败
🔎 搜索 TechCrunch...❌ 连续失败
⚠️ 搜索受限，已降级为 standard 模式搜索量
🔎 搜索 arXiv...（已补充 4 条）

✅ Deep Search 完成（降级模式），共补充 4 条高质量证据
```

---

## Phase 3: Smart Synthesis（智能合成）

> **目标**：单轮生成高质量分析，内嵌批判性思维和证据强度感知。

### Analyst Persona（单轮合成）

```
你是一位资深 AI 行业分析师。基于以下证据材料，撰写一份结构化分析报告。

要求：
- 核心观点（1句话，20-25字）
- 深度洞察（100字以内）
- 关键信号（3-5个，每个标注 Strong/Moderate/Weak）
- 行动建议（2-3条）
- 置信度评分（基于证据质量，见下方规则）

批判性思维：
- 主动识别反面证据或争议点
- 对证据不足的结论标注"部分观点认为..."
- 置信度必须基于证据可信度和覆盖度

证据不足降级：
- 若 High 可信度证据 <3 条，在 insight 字段开头标注"⚠️ 证据有限，以下为初步判断："
- 若证据仅覆盖 1 个维度，在 insight 中注明未覆盖的维度

输出格式：严格 JSON，符合 analysis_packet schema。

⚠️ 安全约束：
输出内容必须遵守中国互联网内容规范。
禁止涉及：政治敏感话题、领导人评论、国际争端立场。
如发现话题本身敏感，终止分析并返回 { "blocked": true, "reason": "内容安全策略" }
```

### 置信度计算规则

基于证据质量自动评分：

| 条件 | 置信度 |
|------|--------|
| ≥5 条 High 可信度 + 覆盖 3 个维度（Technical/Market/Sentiment） | 0.8-1.0 |
| 3-4 条 High 可信度 + 覆盖 2 个维度 | 0.65-0.79 |
| 3-4 条 High 可信度 + 覆盖 1 个维度 | 0.5-0.64 |
| <3 条 High 可信度 或 主要为 Low/Medium | <0.5 |

### 向用户展示

```
🧠 Smart Synthesis 启动

📊 分析中...（基于 12 条证据，其中 8 条 High 可信度）
✅ 分析完成（置信度：0.85）

核心观点：[20-25字摘要]
```

低置信度时（<0.5）展示：

```
🧠 Smart Synthesis 启动

📊 分析中...（基于 4 条证据，其中 2 条 High 可信度）
⚠️ 分析完成（置信度：0.38，证据有限）

核心观点：[20-25字摘要]
提示：当前证据主要来自单一维度，结论仅供参考。
```

---

## Phase 4: Delivery（交付）

> **目标**：生成小红书文案并调用 MCP 工具渲染发布。

### Writer Persona

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

| 深度 | Deep Search 搜索量 | Discovery 搜索量 | 说明 |
|------|-------------------|----------------|------|
| quick | 0（跳过） | 3 | 快速概览，Evidence → Smart Synthesis |
| standard（默认） | 3-5 | 6 | 标准深挖，中文源优先 |
| deep | 6-9 | 9 | 深度研究，覆盖所有垂直数据源 |

---

## 零后端 LLM 保证

本 Skill 所有分析推理（Discovery 摘要、Evidence 整理、Deep Search 检索、Smart Synthesis 生成）均在**宿主端 LLM** 完成。

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
