# Team Research: skill-driven-architecture

## 增强后的需求

将 AIInSight 从"后端 LangGraph workflow 驱动 + Skill 薄壳"重构为"完全 Skill 驱动 + 云端能力层"架构：

- **搜索层**：用宿主端通用 web search（WebSearch/Exa/WebFetch）替代后端 7+ Python 采集器
- **辩论层**：宿主端 LLM 在 Skill 中直接执行 analyst/debater 多轮对弈
- **文案层**：宿主端 LLM 直接写小红书文案，不经后端 writer 节点
- **AI Daily**：整个日报流程也 Skill 驱动（搜索→LLM 去重/评分/聚类/排名→选题→深挖→卡片）
- **云端保留**：renderer（卡片渲染）、XHS MCP（登录/发布/账号管理）、账号隔离
- **目标环境**：Claude Code + OpenCode

## 约束集

### 硬约束

- [HC-1] **renderer 不可 Skill 化** — renderer 依赖 Playwright headless browser + Node.js 渲染栈（`renderer/` 目录），宿主端无法运行。必须保留为云端 MCP 工具。— 来源：代码审查 `renderer/`、`card_render_client.py`

- [HC-2] **XHS 发布不可 Skill 化** — XHS MCP 依赖 Playwright + Chromium 操控小红书 Web 端 API，需要持久化 SQLite session、多账号池管理。必须保留为云端服务。— 来源：`docs/XHS_MCP_Architecture.md`、`xiaohongshu_publisher.py`

- [HC-3] **宿主端需要 web search 能力（前置 MCP 要求）** — Skill 驱动的搜索依赖宿主端有可用的 web search 工具。Claude Code 内置 WebSearch/Exa；OpenCode 需用户配置 search MCP（如 Exa MCP Server、Tavily MCP 等）。Skill 文档需声明此前置依赖。— 来源：环境差异分析、用户确认

- [HC-4] **Skill 无法直接执行 Python 代码** — Skill 是 markdown 指导文档，宿主端 LLM 通过工具调用执行操作。当前评分/聚类逻辑是 Python 算法，但这些逻辑（关键词相关性判断、相似话题合并、重要性排序）LLM 天然擅长，可用 LLM 推理替代而非暴露为 MCP 工具。— 来源：`ai_news_scorer.py`、`ai_topic_cluster.py`

- [HC-5] **卡片渲染需要结构化数据** — renderer 接收的 payload 是严格的 JSON schema（`title`, `summary`, `insight`, `signals`, `actions`, `confidence`, `tags` 等字段）。Skill 写出的文案需要直接输出结构化格式，或在 prompt 中约束输出 schema。— 来源：`card_render_client.py:render_impact()`、`topic_card_builder.py`

### 软约束

- [SC-1] **通用 web search 覆盖度不如专用采集器** — 当前 9 个采集器针对特定网站结构优化（AIbase RSS、机器之心列表页、GitHub Trending API、HF Papers daily endpoint 等）。通用 WebSearch 可能遗漏小众中文 AI 媒体的最新文章。可接受：Skill 通过针对性搜索词（如 `site:aibase.com`）部分补偿。— 来源：`collectors/` 目录审查

- [SC-2] **LLM 评分/排名不可复现** — 当前评分用确定性算法，同一输入同一结果。LLM 替代后同一天两次运行可能产生不同排名。可接受：AI Daily 通常每天只运行一次，不可复现性影响有限。— 来源：`ai_news_scorer.py`、`ai_topic_cluster.py`

- [SC-3] **当前 ai-topic-analyzer Skill 已有 debate 编排模板** — 已有 analyst/debater prompt 模板和终止条件（PASS 或 max_rounds），可直接复用。— 来源：`ai-topic-analyzer/SKILL.md:96-108`

- [SC-4] **host_analysis_pipeline.py 已实现部分 Skill 化基础** — `HostAnalysisState`、`run_host_reasoning_pipeline`、`HostCapabilityClient` 已将推理和能力调用分离。可作为 Skill prompt 设计的参考。— 来源：`host_analysis_pipeline.py`

### 依赖关系

- [DEP-1] **renderer ← 结构化文案** — renderer 需要 JSON payload（title/summary/insight/signals/actions），Skill 的文案写作 prompt 需直接输出此格式
- [DEP-2] **XHS 发布 ← renderer 产出** — 发布需要卡片图片 URL，卡片由 renderer 生成
- [DEP-3] **账号管理 ← MCP Gateway** — 多账号隔离仍依赖云端 Gateway 的 API key → account_id 映射

### 风险

- [RISK-1] **搜索覆盖退化（中文源）** — 通用 web search 可能遗漏 AIbase/机器之心/量子位的当日新闻列表页。缓解：Skill 中使用 `site:aibase.com` 等定向搜索词；也可保留中文源采集器作为可选云端 MCP fallback
- [RISK-2] **上下文窗口压力（AI Daily）** — 如果 web search 返回大量结果（100+ 条标题/摘要），加上多轮 debate，可能逼近上下文窗口上限。缓解：分批搜索、每批让 LLM 摘要后再合并；控制每次 web search 返回条数
- [RISK-3] **文案结构化解析** — Skill 让 LLM 写文案后需要输出 renderer JSON schema。缓解：在写作 prompt 中直接要求输出结构化 JSON，而非自由文本再解析
- [RISK-4] **OpenCode 兼容性** — OpenCode 用户必须配置 search MCP 才能使用搜索功能。缓解：Skill 文档明确声明前置依赖；提供推荐的 search MCP 配置示例

## 成功判据

- [OK-1] 单话题分析全流程（搜索→debate→文案→卡片→发布）可在 Claude Code 中通过 Skill 完成，零后端 LLM 调用
- [OK-2] AI Daily 日报生成（web search→LLM 排名→选题→深挖→卡片）可在 Claude Code 中通过 Skill 完成，零后端 LLM 调用
- [OK-3] 云端仅接收 renderer 请求和 XHS 发布/登录请求，不执行 LLM 推理
- [OK-4] OpenCode 用户配置 search MCP 后可获得同等搜索能力
- [OK-5] 卡片渲染质量与当前后端生成的一致（结构化 JSON payload 正确）
- [OK-6] 后端代码中 `workflow.py` 的 LangGraph 图、7+ collectors、LLM 调用节点、评分/聚类模块可被标记为 deprecated

## 开放问题（已解决）

- Q1: 搜索层怎么处理？ → A: 用宿主端通用 web search 替代 → 约束：[HC-3], [RISK-1]
- Q2: 谁写文案？ → A: 宿主端 LLM 直接写 → 约束：[HC-5], [RISK-3]
- Q3: AI Daily 也 Skill 驱动？ → A: 是，完全 Skill 化 → 约束：[SC-2], [RISK-2]
- Q4: 目标环境？ → A: Claude Code + OpenCode → 约束：[HC-3], [RISK-4]
- Q5: 采集器逻辑写进 Skills 具体含义？ → A: Skill 用通用 web search 替代 → 约束：[SC-1], [RISK-1]
- Q6: AI Daily 链路是否太长？ → A: 不长。LLM 天然擅长去重/评分/聚类/排名，可合并为一个推理步骤。完全 Skill 化可行。

## 架构方案（统一 Tier — 完全 Skill 驱动）

### 设计理念

所有 AI 推理（搜索编排、去重/评分/聚类/排名、debate、文案写作）全部在宿主端 Skill 中完成。云端退化为纯能力服务层，只提供 renderer 和 XHS 两类不可替代的基础设施。

### 单话题分析 Skill 流程

```
1. web search（3-5 次，覆盖中英文 AI 新闻/论文/GitHub）
2. LLM 整理证据摘要
3. LLM analyst 初始分析
4. LLM debater 反驳/补盲点（2-4 轮，PASS 终止）
5. LLM writer 输出结构化文案（直接 JSON schema）
6. MCP render_card（云端渲染）
7. MCP publish_to_xhs（云端发布，需用户确认）
```

### AI Daily Skill 流程

```
1. 3-5 次 web search（"today AI news"、"AI papers today"、"AI github trending" + 中文源定向搜索）
2. LLM 一次性完成：去重 + 评估重要性 + 聚类相似话题 + 排名 Top 10
3. 展示排名列表给用户
4. 用户选题 → 走单话题分析 Skill 流程
5. MCP render_card（云端渲染排名卡片 / 话题卡片）
6. MCP publish_to_xhs（云端发布，需用户确认）
```

### 云端保留的 MCP 工具清单（极简）

| 工具 | 说明 | 来源 |
|------|------|------|
| `render_card` | 卡片渲染（title/impact/radar/timeline/daily-rank/hot-topic） | [HC-1] |
| `publish_to_xhs` | 小红书发布 | [HC-2] |
| `check_xhs_status` | XHS 登录状态 | [HC-2] |
| `get_xhs_login_qrcode` | XHS 二维码 | [HC-2] |
| `check_xhs_login_session` | XHS 登录轮询 | [HC-2] |
| `submit_xhs_verification` | XHS 验证码 | [HC-2] |

注意：不再需要 `collect_ai_news`、`search_ai_news`、`analyze_topic`、`host_analyze_topic`、`retrieve_and_report`、`submit_analysis_result`、`get_analysis_status`、`get_analysis_result` 等工具。它们的职责全部由 Skill 承担。

### 前置 MCP 要求

Skill 文档需声明以下前置依赖：
- **web search 工具**：Claude Code 内置 WebSearch/Exa 满足；OpenCode 需配置 search MCP（推荐 Exa MCP Server 或 Tavily MCP）
- **远程 MCP Gateway**：提供 renderer + XHS 能力（或本地 docker compose 开发模式）

### 可淘汰的后端模块

| 模块 | 原因 |
|------|------|
| `app/services/workflow.py` LangGraph 图 | Skill 编排替代 |
| `reporter_node`, `analyst_node`, `debater_node`, `writer_node` | LLM 推理移到宿主端 |
| `host_analysis_pipeline.py` 全部 `default_host_*` 函数 | 后端 LLM 调用被 Skill 替代 |
| `opinion_mcp/tools/analyze.py` 中 `analyze_topic`, `host_analyze_topic`, `retrieve_and_report`, `submit_analysis_result` | Skill 直接编排 |
| `app/services/topic_evidence_retriever.py` | web search 替代 |
| `app/services/ai_daily_pipeline.py` | Skill 替代采集+排名 |
| `app/services/ai_news_scorer.py` | LLM 替代评分 |
| `app/services/ai_topic_cluster.py` | LLM 替代聚类 |
| `app/services/collectors/*` (9 个采集器) | web search 替代 |
| `app/services/ai_daily_cache.py` | Skill 不需要后端缓存 |
| `app/services/content_extractor.py` | LLM 直接处理搜索结果 |

### 需保留的后端模块

| 模块 | 原因 |
|------|------|
| `card_render_client.py` | renderer HTTP 代理层 |
| `xiaohongshu_publisher.py` | XHS 发布代理层 |
| `account_context.py` | 多账号隔离 |
| `topic_card_builder.py` | 结构化 payload 构建（可能也移到 Skill 侧） |
| `renderer/` | 卡片渲染服务本体 |
| `opinion_mcp/server.py` | MCP Gateway（精简后只注册 render + XHS 工具） |
| `publish/ai_daily_publish_service.py` | 发布编排（精简后只保留渲染+发布调用） |
