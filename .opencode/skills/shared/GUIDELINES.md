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
      "card_type": "title | verdict | evidence | delta | action | hot-topic | impact | daily-rank | radar | timeline",
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

#### `verdict`
```json
{
  "title": "标题",
  "verdict": "20-25字核心判断",
  "why_now": "为什么这件事值得现在讲",
  "confidence": 0.82,
  "caveat": "结论边界 / 风险提醒",
  "stance": "当前立场",
  "tags": ["#AI"]
}
```

#### `evidence`
```json
{
  "title": "标题",
  "entries": [
    {
      "claim": "关键证据",
      "detail": "这条证据支持了什么判断",
      "source": "来源名",
      "strength": "High"
    }
  ],
  "takeaway": "证据整体说明了什么",
  "tags": ["#AI"]
}
```

#### `delta`
```json
{
  "title": "标题",
  "opening": "初版判断",
  "challenge": "最大质疑",
  "revision": "修正结论",
  "resolution": "为什么最后这样收束",
  "confidence": 0.82
}
```

#### `action`
```json
{
  "title": "标题",
  "strategy": "一句话执行策略",
  "actions": ["现在就做什么"],
  "watchouts": ["重点风险 / 观察点"],
  "audience": "适用对象",
  "tags": ["#AI"]
}
```

#### `impact`
```json
{
  "title": "标题",
  "summary": "20-25字摘要",
  "insight": "100字洞察",
  "signals": ["信号名称"],
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
  "date": "YYYY-MM-DD"
}
```

#### `daily-rank`
```json
{
  "date": "YYYY-MM-DD",
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
    { "round": 1, "title": "关键转折", "summary": "本轮发生了什么修正" }
  ]
}
```

> 说明：`impact` / `timeline` 仍保留兼容，但单话题默认推荐使用 `title + verdict + evidence + delta`，`action` 作为可选扩展卡。

**Output Schema:**

```json
{
  "gallery_url": "http://...",
  "results": [
    {
      "success": true,
      "output_path": "/path/to/image.png",
      "image_url": "http://..."
    }
  ]
}
```

> ⚠️ **重要**：输出返回 `output_path` / `image_url` / `gallery_url`，**不返回 base64**（避免撑爆 LLM 上下文）。

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
  "topic_id": "YYYYMMDD_abc123",
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
    "timeliness": 10,
    "total": 8.6
  },
  "source_urls": ["https://..."],
  "topic_id": "YYYYMMDD_hash8chars"
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
- Timeliness（时效性）：距今越近分越高
  - 今天发布 → 9-10 分
  - 昨天发布 → 6-8 分
  - 日期未知 → 上限 5 分

输出格式：JSON { "novelty": N, "impact": N, "credibility": N, "timeliness": N, "total": N, "reasoning": "一句话理由" }
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
| **Technical** | `"{topic}" latest development {current_year}` | `"{topic}" 技术进展 最新 {current_year}` |
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

### 4.4 Deep Search（垂直数据源深度检索）

话题分析的 Phase 2.5 阶段，针对热点从垂直数据源执行定向 `site:` 搜索：

| 类型 | 数据源 | 搜索语法 |
|------|--------|---------|
| **中文 AI 媒体** | AIBase | `"{topic}" site:aibase.com` |
| | 机器之心 | `"{topic}" site:jiqizhixin.com` |
| | 量子位 | `"{topic}" site:qbitai.com` |
| **英文技术源** | TechCrunch | `"{topic}" site:techcrunch.com` |
| | arXiv | `"{topic}" site:arxiv.org abstract {current_year}` |
| | GitHub | `"{topic}" site:github.com trending` |

**模式搜索量：**

| 模式 | Deep Search 搜索量 | 策略 |
|------|-------------------|------|
| quick | 0（跳过） | — |
| standard | 3-5 次 | 中文源优先 |
| deep | 6-9 次 | 覆盖所有数据源 |

**去重规则：** 按 URL 去重 → 按事件合并（保留所有 URL）→ 按时间排序插入。

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

## 6. 置信度评估规则

Smart Synthesis 阶段基于证据质量自动计算置信度评分：

| 条件 | 置信度 |
|------|--------|
| ≥5 条 High 可信度 + 覆盖 3 个维度（Technical/Market/Sentiment） | 0.8-1.0 |
| 3-4 条 High 可信度 + 覆盖 2 个维度 | 0.65-0.79 |
| 3-4 条 High 可信度 + 覆盖 1 个维度 | 0.5-0.64 |
| <3 条 High 可信度 或 主要为 Low/Medium | <0.5 |

**可信度分级：**

| 等级 | 来源类型 |
|------|---------|
| **High** | 主流科技媒体、官方博客、论文（TechCrunch、机器之心、arxiv.org 等） |
| **Medium** | 社区讨论、行业分析（HN、Reddit、知乎） |
| **Low** | 个人博客、未经证实的报道 |

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
