# Shared Guidelines — Capability Contract & Shared Schemas

> **Scope**: This file defines the canonical contracts for all agent skills in this project.
> All skills MUST conform to these definitions. Any deviation is a breaking change.

---

## 1. Capability Contract（MCP 工具定义）

### 1.1 `render_cards`

渲染可视化卡片，支持多种 card_type。

**Input Schema:**

```json
{
  "specs": [
    {
      "card_type": "hot-topic | impact | title | daily-rank | radar | timeline",
      "payload": {}
    }
  ]
}
```

**Minimal valid payload per card_type:**

#### `title`
```json
{
  "title": "4-8字标题",
  "emoji": "🔍",
  "theme": "warm"
}
```

#### `impact`
```json
{
  "title": "标题",
  "summary": "20-25字摘要",
  "insight": "100字洞察",
  "signals": [
    { "label": "信号名称", "value": "Strong" }
  ],
  "actions": ["行动建议"],
  "confidence": 0.95,
  "tags": ["#AI"]
}
```

#### `hot-topic`
```json
{
  "title": "标题",
  "summary": "摘要",
  "tags": [],
  "sourceCount": 5,
  "score": 8.5,
  "date": "2025-01-01"
}
```

#### `daily-rank`
```json
{
  "date": "2025-01-01",
  "topics": [
    { "rank": 1, "title": "话题", "score": 9.0, "tags": ["AI"] }
  ],
  "title": "AI 每日热点"
}
```

#### `radar`
```json
{
  "labels": ["维度1", "维度2"],
  "datasets": [
    { "label": "数据集", "data": [80, 60] }
  ]
}
```

#### `timeline`
```json
{
  "timeline": [
    { "time": "10:00", "event": "事件描述", "impact": "high" }
  ]
}
```

**Output Schema:**

```json
{
  "results": [
    {
      "success": true,
      "output_path": "/path/to/image.png",
      "image_url": "http://..."
    }
  ]
}
```

> ⚠️ **重要**：输出只返回 `output_path` + `image_url`，**不返回 base64**（避免撑爆 LLM 上下文）。

---

### 1.2 `publish_xhs_note`

发布小红书笔记（接受原始内容，不再接受 job_id）。

**Input Schema:**

```json
{
  "title": "标题",
  "content": "正文",
  "images": ["path1.png", "path2.png"],
  "tags": ["#标签1"],
  "account_id": "账号ID（可选，用于多账号场景）"
}
```

**Output Schema:**

```json
{
  "success": true,
  "note_url": "https://..."
}
```

---

### 1.3 `check_xhs_status`

检查 XHS 登录状态。

**Input Schema:**

```json
{
  "account_id": "账号ID（可选，用于多账号场景）"
}
```

**Output Schema:**

```json
{
  "mcp_available": true,
  "login_status": true
}
```

---

### 1.4 `get_xhs_login_qrcode`

获取 XHS 登录二维码。

**Input Schema:**

```json
{
  "account_id": "账号ID（可选，用于多账号场景）"
}
```

**Output Schema:**

```json
{
  "success": true,
  "session_id": "...",
  "qr_ascii": "...",
  "expires_at": "..."
}
```

---

### 1.5 `check_xhs_login_session`

轮询扫码登录状态。

**Input Schema:**

```json
{
  "session_id": "...",
  "account_id": "账号ID（可选，用于多账号场景）"
}
```

**Output Schema:**

```json
{
  "status": "pending | logged_in | expired"
}
```

---

### 1.6 `submit_xhs_verification`

提交短信验证码。

**Input Schema:**

```json
{
  "session_id": "...",
  "code": "123456",
  "account_id": "账号ID（可选，用于多账号场景）"
}
```

**Output Schema:**

```json
{
  "success": true
}
```

---

## 2. Skill 侧输出契约

### 2.1 `analysis_packet`（单话题分析输出）

```json
{
  "topic_id": "20250325_abc123",
  "title": "4-8字主标题",
  "subtitle": "副标题",
  "summary": "20-25字核心观点",
  "insight": "100字深度洞察",
  "signals": [
    {
      "label": "信号名",
      "value": "Strong | Moderate | Weak",
      "desc": "上下文描述"
    }
  ],
  "actions": ["用户行动建议1", "建议2"],
  "confidence": 0.95,
  "tags": ["#AI", "#标签"],
  "xhs_copy": {
    "title": "小红书标题（含emoji）",
    "content": "小红书正文（800-1200字）",
    "tags": ["标签1", "标签2"]
  },
  "debate_log": [
    "Round 1: Analyst: ...",
    "Debater: ...",
    "Round 2: ..."
  ],
  "sources": ["https://source1.com", "https://source2.com"]
}
```

---

### 2.2 `daily_topics[]`（日报话题列表）

```json
{
  "canonical_title": "话题标准名称",
  "summary_zh": "一句话中文摘要",
  "tags": ["AI", "LLM"],
  "score_breakdown": {
    "novelty": 8,
    "impact": 9,
    "credibility": 7,
    "total": 8.0
  },
  "source_urls": ["https://..."],
  "topic_id": "20250325_hash8chars"
}
```

---

### 2.3 `topic_id` 生成规则

```
topic_id = YYYYMMDD_ + SHA1(canonical_title)[0:8]
```

- 日期部分取分析执行当日日期（UTC+8）
- 哈希部分取 `canonical_title` 字符串的 SHA1 前 8 位十六进制字符
- **不依赖后端**，Skill 侧在构造 `analysis_packet` 时自行生成

---

## 3. Persona Prompt 模板

### 3.1 Analyst（分析师）

```
你是一位资深 AI 行业分析师。基于以下证据材料，撰写一份结构化分析报告。

要求：
- 核心观点（1句话，20-25字）
- 深度洞察（100字以内）
- 关键信号（3-5个，每个标注 Strong/Moderate/Weak）
- 行动建议（2-3条）
- 置信度评分（0-1）

输出格式：严格 JSON，符合 analysis_packet schema。
```

---

### 3.2 Debater（辩论者）

```
你是一位批判性思维专家。你的任务是挑战分析师的观点，找出逻辑漏洞和遗漏证据。

规则：
- 每轮提出 2-3 个具体质疑
- 质疑必须基于证据，不能空洞反驳
- 如果分析师的观点经得起检验，回复 "PASS"

输出格式：逐条质疑 + 理由，或 "PASS"
```

---

### 3.3 Evaluator（评估者）

```
你是一位新闻评分专家。对以下 AI 新闻/话题进行评分。

评分维度（1-10分）：
- Novelty（新颖度）：是否为首次报道/突破性进展
- Impact（影响力）：对行业/用户的实际影响程度
- Credibility（可信度）：信源质量和交叉验证程度

输出格式：JSON { "novelty": N, "impact": N, "credibility": N, "total": N, "reasoning": "一句话理由" }
```

---

### 3.4 Writer（写手）

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

---

## 4. Web Search 编排策略

每个话题执行 3 类搜索，每类包含中英双语 query：

### 4.1 搜索分类

| 类型 | 英文 Query | 中文 Query |
|------|-----------|-----------|
| **Technical** | `"{topic}" latest development 2025` | `"{topic}" 技术进展 最新` |
| **Market** | `"{topic}" market impact industry` | `"{topic}" 市场影响 行业分析` |
| **Sentiment** | `"{topic}" community reaction opinion` | `"{topic}" site:aibase.com OR site:jiqizhixin.com` |

### 4.2 搜索结果处理

每批搜索后**立即摘要**（防止上下文膨胀），格式：

```
[来源] 标题 - 一句话摘要 (日期)
```

### 4.3 日报额外定向搜索

```
"today AI news" site:aibase.com
"今日AI" site:jiqizhixin.com OR site:qbitai.com
"AI" site:techcrunch.com latest
```

---

## 5. 多宿主兼容说明

| 宿主 | Web Search 工具 | 说明 |
|------|----------------|------|
| **Claude Code** | 内置 `WebSearch` 工具 | 可直接调用，无需额外配置 |
| **OpenCode** | 配置 search MCP server（如 `exa-search`） | Skill 通过 `MCP_TOOLS` 能力发现自动适配 |

**通用约定**：所有 Skill 头部必须声明依赖：

```yaml
requires:
  - web_search
  - mcp_gateway
```

Skill 启动时检查 `requires` 中的工具可用性；若不满足，提前 fail-fast 并返回清晰错误信息。

---

## 6. Debate 终止条件

Debate 循环在以下任一条件满足时终止：

1. **Debater 回复 `"PASS"`** → 分析通过，立即终止
2. **达到 `max_rounds`**（默认 3 轮）→ 强制终止，取最新版本的分析结果
3. **单轮无新质疑点**（Debater 重复上一轮的质疑）→ 终止，视为隐式 PASS

终止后，`debate_log` 字段应记录完整的对话历史，格式：

```
Round 1: Analyst: <分析摘要>
Round 1: Debater: <质疑内容>
Round 2: Analyst: <修正版分析>
Round 2: Debater: PASS
```

---

## 7. 安全策略前移规则

### 7.1 Skill Prompt 内嵌安全约束

所有涉及内容生成的 persona prompt 必须包含以下安全块：

```
⚠️ 安全约束：
输出内容必须遵守中国互联网内容规范。
禁止涉及：政治敏感话题、领导人评论、国际争端立场
如发现话题本身敏感，终止分析并返回 { "blocked": true, "reason": "内容安全策略" }
```

### 7.2 MCP 端 Preflight 检查

`publish_xhs_note` 调用前，MCP server 端执行 server-side preflight 内容安全检查：

- 扫描 `title` + `content` 中的敏感关键词
- 命中则拒绝发布并返回：

```json
{
  "success": false,
  "error": "content_policy_violation",
  "reason": "内容安全策略阻止发布"
}
```

### 7.3 阻断优先级

```
Skill prompt 安全约束 → analysis_packet 返回 blocked:true
                     ↓
MCP preflight 检查   → publish_xhs_note 返回 success:false
```

两层防线均须独立运作，不得相互依赖。
