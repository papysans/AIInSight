# Team Plan: skill-driven-architecture

## 概述

将 AIInSight 从"后端 LangGraph workflow + Skill 薄壳"重构为"完全 Skill 驱动 + 云端能力层"：所有 AI 推理在宿主端 Skill 完成，云端退化为 renderer + XHS 纯能力服务。

## Codex 分析摘要

1. **可行性**：推荐方案 A — 保留 FastAPI 作为 capability gateway，精简 opinion_mcp 为 render/XHS facade。改动最小，风险最低
2. **关键发现**：`host_analysis_pipeline.py` 在 main 分支不存在（只在 feat 分支），不应按"已有半成品"估算工期
3. **保留清单**：renderer/server.js、card_render_client.py、xiaohongshu_publisher.py、app/main.py、app/api/endpoints.py（capability 部分）、app/schemas.py（Card/Xhs 部分）
4. **删除清单**：workflow.py 整文件、9 个 collectors 整目录、topic_evidence_retriever.py、ai_daily_pipeline.py、ai_daily_workflow_adapter.py、ai_news_scorer.py、ai_topic_cluster.py、image_generator.py、workflow_status.py、app/llm.py、opinion_mcp/tools/analyze.py、opinion_mcp/tools/ai_daily.py、job_manager.py、webhook_manager.py
5. **安全策略风险**：当前政治敏感词 redaction/blocking 在 workflow.py 中，迁移后需在 Skill prompt 前移 + publish_xhs_note 前加 server-side preflight
6. **publish 接口改造**：publish_to_xhs 应改为接受原始内容（title/content/images/tags），不再接受 job_id — 架构切换关键
7. **Capability contract 先行**：先定死 render_cards 和 publish_xhs_note 的 JSON schema，Skill 以此为准
8. **MCP 最终 5 个工具**：render_cards(specs[])、check_xhs_status、get_xhs_login_qrcode、publish_xhs_note(title/content/images/tags)、reset_xhs_login

## Gemini 分析摘要

1. **Skill 结构**：统一 "Thick-Skill" 模板，ai-topic-analyzer 为 5 阶段引擎（Discovery → Evidence → Crucible → Synthesis → Delivery），ai-insight 为 4 阶段管线（Pulse → Processing → Selection → Delegation）
2. **Prompt 模板**：4 个内部 persona（Analyst/Debater/Evaluator/Writer），每个有严格输出约束
3. **Web Search 策略**：每话题 3 类查询（Technical/Market/Sentiment），中英双语覆盖，每次搜索后立即摘要防止上下文膨胀
4. **JSON Schema**：`topic_card_v2` 结构（title/summary/insight/signals/actions/confidence/tags + metadata）
5. **多宿主兼容**：标准 Markdown Instructions + MCP_TOOLS 能力发现，避免宿主特定 hack
6. **建议**：Skill 应流式展示内部 debate 过程以建立用户信任

## 技术方案

### 架构分层

```
宿主端 Skill (控制面 + 推理面)
  ├─ web search → LLM 推理 → 结构化 JSON
  └─ ↓ MCP 调用
云端 MCP Server (能力面，极简)
  ├─ render_card → renderer 服务
  └─ XHS 工具集 → xhs-mcp sidecar
```

### 关键技术决策

1. **Skill 是唯一编排入口**：不再有 `analyze_topic`、`get_ai_daily` 等后端推理工具
2. **MCP Server 精简为 6 个工具**：render_card, publish_to_xhs, check_xhs_status, get_xhs_login_qrcode, check_xhs_login_session, submit_xhs_verification
3. **结构化输出约束**：Skill prompt 要求 LLM 输出 renderer 兼容的 JSON schema
4. **web search 前置依赖**：Claude Code 内置 WebSearch/Exa 满足；OpenCode 需配置 search MCP
5. **debate 流式展示**：Skill 指导 LLM 在 debate 过程中向用户输出中间推理

### Renderer JSON Payload Schema

```json
{
  "card_type": "hot-topic|impact|title|daily-rank|radar|timeline",
  "payload": {
    "title": "4-8字主标题",
    "summary": "20-25字核心观点",
    "insight": "100字深度洞察",
    "signals": [{"label": "信号名", "value": "Strong|Weak", "desc": "上下文"}],
    "actions": ["用户行动建议"],
    "confidence": 0.95,
    "tags": ["#AI", "#标签"]
  }
}
```

## 子任务列表

### Task 1: Capability Contract + 共享 schema 与 prompt 模板

- **类型**: 前端/Skill + 后端契约
- **文件范围**:
  - `NEW: .agents/skills/shared/GUIDELINES.md`
- **依赖**: 无
- **实施步骤**:
  1. 创建 `.agents/skills/shared/` 目录
  2. 编写 `GUIDELINES.md`，包含：
     - **Capability Contract**（Codex 建议先行定义）：
       - `render_cards` 输入/输出 JSON schema（每种 card_type 的最小合法样例）
       - `publish_xhs_note` 输入/输出 JSON schema（title/content/images/tags，不接受 job_id）
     - **Skill 侧输出契约**：
       - `analysis_packet` 结构（summary/insight/title/subtitle/xhs_copy/tags 等）
       - `daily_topics[]` 结构（canonical_title/summary_zh/tags/score_breakdown/source_urls/topic_id）
       - `topic_id` 生成规则：日期 + canonical_title hash，不依赖后端
     - 4 个 persona prompt 模板（Analyst/Debater/Evaluator/Writer）及其输出格式约束
     - web search 编排策略（3 类查询：Technical/Market/Sentiment，中英文源覆盖）
     - 多宿主兼容说明（Claude Code vs OpenCode 差异处理）
     - debate 终止条件规则（PASS 或 max_rounds）
     - 安全策略前移规则（政治敏感词在 Skill prompt 中处理）
- **验收标准**: GUIDELINES.md 完成，Capability Contract 被 Task 2/3/4 共同引用

### Task 2: ai-topic-analyzer Skill 重写

- **类型**: 前端/Skill
- **文件范围**:
  - `REWRITE: .agents/skills/ai-topic-analyzer/SKILL.md`
- **依赖**: Task 1
- **实施步骤**:
  1. 重写 SKILL.md 为 5 阶段"厚壳"流程：
     - Phase 1 Discovery: 指导 LLM 执行 3-5 次 web search（Technical/Market/Sentiment）
     - Phase 2 Evidence: 指导 LLM 整理证据摘要（Fact Sheet）
     - Phase 3 Crucible: 指导 LLM 执行 Analyst → Debater 多轮对弈（2-4 轮，PASS 终止）
     - Phase 4 Synthesis: 指导 LLM 输出小红书文案 + renderer JSON payload
     - Phase 5 Delivery: 调用 MCP render_card → publish_to_xhs
  2. 引用 shared/GUIDELINES.md 的 persona 模板和 JSON schema
  3. 保留小红书登录流程（check_xhs_status → qrcode → session → verification）
  4. 声明 MCP 前置依赖（web search + 远程 MCP Gateway）
- **验收标准**: 用户说"帮我看看 xxx 这个话题"时，Skill 指导 LLM 完整走完 5 阶段，零后端 LLM 调用

### Task 3: ai-insight Skill 重写

- **类型**: 前端/Skill
- **文件范围**:
  - `REWRITE: .agents/skills/ai-insight/SKILL.md`
- **依赖**: Task 1, Task 2（复用单话题分析流程）
- **实施步骤**:
  1. 重写 SKILL.md 为 4 阶段日报管线：
     - Phase 1 Pulse: 3-5 次 web search（"today AI news" + 中文源定向搜索 site:aibase.com 等）
     - Phase 2 Processing: LLM 一次性完成去重 + 评分（Novelty/Impact/Credibility）+ 聚类 + 排名 Top 10
     - Phase 3 Selection: 展示排名列表给用户，等待选题
     - Phase 4 Delegation: 选题后转入 ai-topic-analyzer 的 Phase 1-5 流程
  2. 榜单卡片支持：LLM 输出 daily-rank 类型的 JSON payload
  3. 保留 /ai-daily、/analyze、/publish、/publish-today 命令语义
- **验收标准**: 用户说"今日AI有什么热点"时，Skill 指导 LLM 完整走完 4 阶段，零后端 LLM 调用

### Task 4: MCP Server 精简 + Capability API 收口

- **类型**: 后端
- **文件范围**:
  - `MODIFY: opinion_mcp/server.py` — 重写 MCP_TOOLS 和 TOOL_HANDLERS，只留 5 个工具
  - `MODIFY: opinion_mcp/tools/__init__.py` — 精简导出
  - `MODIFY: opinion_mcp/tools/publish.py` — publish_to_xhs 改为接受原始内容（title/content/images/tags），不再接受 job_id
  - `NEW: opinion_mcp/tools/render.py` — 新增 render_cards 工具（调用 card_render_client，带 schema 校验）
  - `MODIFY: opinion_mcp/services/backend_client.py` — 只保留 render/XHS client，删除 call_analyze_api 等
  - `MODIFY: opinion_mcp/config.py` — 删除 SOURCE_GROUPS/DEPTH_PRESETS 等分析配置，只保留 capability 连接配置
  - `DELETE: opinion_mcp/tools/analyze.py` — 整文件
  - `DELETE: opinion_mcp/tools/ai_daily.py` — 整文件
  - `DELETE: opinion_mcp/services/job_manager.py` — 整文件
  - `DELETE: opinion_mcp/services/webhook_manager.py` — 整文件
  - `MODIFY: opinion_mcp/tools/settings.py` — 删除或精简
  - `MODIFY: app/api/endpoints.py` — 删除 /analyze、/retrieve-and-report、/submit-analysis-result、/workflow/status、/ai-daily/*、/topic/cards 端点
  - `MODIFY: app/schemas.py` — 删除 TopicAnalysisRequest/AgentState/Evidence*/DailyTopic/AiDaily* 等
  - `MODIFY: app/config.py` — 删除后端 LLM/provider/source/depth/workflow 配置
- **依赖**: Task 1（Capability Contract 定义）
- **实施步骤**:
  1. 按 Task 1 的 Capability Contract 实现 `render_cards` 工具（schema 校验 → card_render_client 调用）
  2. 改造 `publish_to_xhs` 为 `publish_xhs_note`：输入 title/content/images/tags，不接受 job_id
  3. 在 server.py 中重写 MCP_TOOLS（只 5 个）和 TOOL_HANDLERS
  4. 删除 analyze.py、ai_daily.py、job_manager.py、webhook_manager.py
  5. 精简 backend_client.py、config.py
  6. 精简 app/api/endpoints.py：只保留 render/XHS capability 端点 + health
  7. 精简 app/schemas.py、app/config.py：删除分析相关 schema 和配置
  8. 在 render_cards 返回中只给 output_path + image_url，不返回 base64（避免撑爆 LLM 上下文）
  9. 保留 /health、/readiness、MCP SSE/JSON-RPC 协议端点
- **验收标准**: MCP Server 只暴露 5 个工具，/health 正常，publish 不再接受 job_id

### Task 5: Legacy 模块删除

- **类型**: 后端
- **文件范围**:
  - `DELETE: app/services/workflow.py` — LangGraph 图整文件
  - `DELETE: app/services/topic_evidence_retriever.py` — 整文件
  - `DELETE: app/services/ai_daily_pipeline.py` — 整文件
  - `DELETE: app/services/ai_daily_workflow_adapter.py` — 整文件
  - `DELETE: app/services/ai_news_scorer.py` — 整文件
  - `DELETE: app/services/ai_topic_cluster.py` — 整文件
  - `DELETE: app/services/ai_daily_cache.py` — 整文件
  - `DELETE: app/services/content_extractor.py` — 整文件
  - `DELETE: app/services/image_generator.py` — 整文件
  - `DELETE: app/services/workflow_status.py` — 整文件
  - `DELETE: app/services/collectors/` — 整目录（9 个采集器）
  - `DELETE: app/services/publish/ai_daily_publish_service.py` — 整文件
  - `DELETE: app/services/host_analysis_pipeline.py` — 整文件（如存在）
  - `DELETE: app/llm.py` — 后端不再做 LLM reasoning
  - `MODIFY: app/services/__init__.py` — 清理导入
- **依赖**: Task 4（确保 MCP/API 不再引用这些模块）
- **实施步骤**:
  1. 确认 Task 4 完成后，app/api 和 opinion_mcp 不再 import 以上模块
  2. 一次性删除所有 legacy 文件
  3. 清理 app/services/__init__.py 中的残留导入
  4. 运行 `python -c "import app"` 验证无 import 报错
- **验收标准**: 所有 legacy 文件已删除，`import app` 无报错，git diff 干净

### Task 6: 端到端验证

- **类型**: 测试
- **文件范围**:
  - `NEW: tests/test_skill_driven_contract.py` — Skill JSON schema 契约测试
  - `MODIFY: tests/test_host_entrypoint_docs_contract.py` — 更新契约
- **依赖**: Task 2, Task 3, Task 4
- **实施步骤**:
  1. 编写 JSON schema 契约测试：验证 Skill 输出的 renderer payload 结构正确
  2. 编写 MCP 工具清单测试：验证 server.py 只暴露 6 个工具
  3. 更新 host_entrypoint 契约测试适配新架构
- **验收标准**: 所有契约测试通过

## 文件冲突检查

✅ 无冲突 — 每个 Task 的文件范围隔离：
- Task 1: `.agents/skills/shared/` (新建)
- Task 2: `.agents/skills/ai-topic-analyzer/SKILL.md`
- Task 3: `.agents/skills/ai-insight/SKILL.md`
- Task 4: `opinion_mcp/` 目录
- Task 5: `app/services/` 目录
- Task 6: `tests/` 目录

## 并行分组

- **Layer 1 (并行)**: Task 1, Task 4
- **Layer 2 (依赖 Layer 1)**: Task 2, Task 5
- **Layer 3 (依赖 Layer 2)**: Task 3
- **Layer 4 (依赖 Layer 3)**: Task 6

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 通用 web search 覆盖度不如专用采集器（中文源） | Skill 使用 `site:aibase.com` 等定向搜索词补偿 |
| 上下文窗口压力（AI Daily 大量搜索结果） | 分批搜索，每批摘要后合并；控制每次返回条数 |
| LLM 评分/排名不可复现 | 固定评分 rubric + 固定输出 schema + golden fixtures 回归测试 |
| 文案结构化解析风险 | Skill prompt 直接要求输出 JSON；MCP 端严格 schema 校验 |
| **安全策略回退**（Codex 发现） | 政治敏感词 redaction 前移到 Skill prompt；publish_xhs_note 前加 server-side preflight |
| 会话状态丢失（topic/job 无后端状态） | topic_id 用日期+title hash 生成；日报 manifest 作为 artifact 存储 |
| render payload 被 prompt 写坏 | MCP 端按 schema 严格校验；Skill 内嵌每种 card 的最小合法样例 |
| OpenCode 兼容性 | Skill 声明前置依赖；提供 search MCP 配置示例 |
