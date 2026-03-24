## Context

当前 AIInSight 的默认运行方式是本地 `docker compose` 四服务栈：

- `api`：分析工作流、卡片生成调度、XHS API
- `mcp`：对外暴露 `analyze_topic`、`publish_to_xhs`、`check_xhs_status` 等工具
- `renderer`：Playwright 卡片渲染服务
- `xhs-mcp`：小红书登录/发布 runtime

当前单话题分析和多轮 Agent 辩论并不在 skill 侧执行，而是在 backend workflow 内统一编排：

- `app/api/endpoints.py:/analyze` 负责启动完整分析工作流并输出 SSE 事件流
- `app/services/workflow.py` 包含 `source_retriever -> reporter -> analyst -> debater -> writer -> image_generator -> xhs_publisher` 图
- `opinion_mcp/tools/analyze.py` 只负责创建 job、调用 `backend_client.call_analyze_api()` 并消费 SSE 事件更新状态

这意味着当前 skill 层本质上只是流程文档，真正的执行边界已经天然集中在后端。用户提出的"方案 A"要求进一步把本地多容器复杂度收敛为"用户只用一个 skill / 一个远程 MCP"，并在开始前评估是否可将多轮 debate 挪到宿主端，以减轻云侧服务负担。

## Goals / Non-Goals

**Goals:**
- 将 AIInSight 演进为"单一远程 MCP Gateway + 内部服务"架构，用户侧只连接一个远程 MCP 入口
- 保留现有工具契约（如 `analyze_topic`、`publish_to_xhs`、`check_xhs_status`）与大部分工作流语义，减少上层调用改动
- 明确云端内部服务边界：`mcp gateway`、`api`、`renderer`、`xhs runtime`、持久化层
- 将多轮 debate 迁移到宿主端执行，消除云端 LLM 推理成本，提升 debate 质量和用户可见性
- 实现多账号管理与租户隔离，确保每个 skill 使用者拥有独立的 XHS 账号、任务空间和用户设置
- 为后续计费系统、远程 skill 使用体验奠定结构基础

**Non-Goals:**
- 本次不直接实现计费系统
- 本次不直接替换所有本地开发体验；本地 `docker compose` 仍可保留为开发模式
- 本次不把现有所有 skill 改造成机器可读 MCP 绑定格式
- 本次不移除 `analyze_topic` 全包式工具；它作为向后兼容路径保留给不具备宿主端 debate 能力的客户端

## Decisions

### D1: 对外只暴露一个远程 MCP Gateway

**选项 A（✅ 选定）**：保留 `opinion_mcp` 作为统一公网入口，对外只提供一个远程 MCP endpoint
- 用户只配置一个远程 MCP，如 `https://mcp.aiinsight.example.com/mcp`
- skill 不再需要推断 `api`、`renderer`、`xhs-mcp` 的具体位置
- `mcp gateway` 继续承载公共工具契约，内部再调用 `api` / `renderer` / `xhs runtime`

**选项 B**：同时向用户暴露多个远程服务（analysis MCP、xhs MCP、renderer API）
- 优点：服务职责最纯
- 缺点：用户心智复杂，skill 仍要"选服务"，违背方案 A 的产品目标

**理由**：最优雅的用户体验不是让 skill 选择多个后端，而是把所有能力收敛到一个远程 MCP Gateway。

### D2: api / renderer / xhs runtime 改为云端内部服务

**选项 A（✅ 选定）**：四服务逻辑保留，但只将 `mcp gateway` 暴露公网，其余全部内网化
- `api`：分析工作流、SSE、发布 orchestration、登录状态 API
- `renderer`：卡片和图片渲染
- `xhs runtime`：小红书登录、session 持久化、发布执行
- persistence：数据库 + 对象存储 + XHS 账号状态持久化

**选项 B**：把所有逻辑合并成一个巨型服务
- 优点：部署单元更少
- 缺点：渲染/XHS runtime 与分析工作流耦合度更高，不利于故障隔离和后续扩展

**理由**：保留内部服务边界，能最大限度复用现有代码，同时对用户隐藏复杂度。

### D3: 多轮 debate 迁移到宿主端执行

**选项 A**：`debate_rounds`、`analyst/debater` orchestration 继续在云端 backend 执行
- 现有实现已绑定 `app/services/workflow.py`
- 与 `job_manager`、`workflow_status`、SSE 进度流天然耦合
- 云端统一执行可保持一致的状态管理、日志
- 缺点：云端承担全部 LLM 推理成本（debate 是最大的 LLM 消耗环节）
- 缺点：debate 对用户不透明（黑盒轮询 get_analysis_status），用户无法实时看到辩论过程或中途干预
- 缺点：云端 LLM 通常弱于宿主端模型（deepseek-chat vs Claude Opus / GPT-4）

**选项 B（✅ 选定）**：把多轮 debate 挪到宿主端执行，云端拆分为"前段 retrieval + reporter"和"后段 writer + cards + publish"两个原子步骤

代码审查结论：debate 的技术本质是一个**纯 LLM prompt 循环**，`analyst_node` 和 `debater_node` 各自只做 `SystemMessage + HumanMessage → llm.ainvoke()`，状态仅为 `initial_analysis`（字符串）+ `critique`（字符串）+ `revision_count`（整数）。不依赖文件系统、数据库、网络服务或任何云端基础设施。

宿主端能力评估：
- 宿主端（OpenCode / Claude Code）本身就是 LLM Agent，天生具备推理能力
- 现有 skill 已证明宿主端能执行 5+ 步多工具编排（确认模式 → analyze_topic → 轮询 status → get_result → generate_cards → publish）
- `opinion_mcp` 层已有 async job tracking、状态管理、webhook 推送等编排基础设施
- debate 状态天然保持在宿主端对话上下文中，无需额外状态存储

实现方式：

```
宿主端 debate 工作流:

Host ──MCP──▶ Gateway ──▶ API
 │                         │
 │  1. retrieve_and_report │ (云端: source_retriever + reporter)
 │◀─── evidence_bundle ────│
 │     + news_content      │
 │                         │
 │  2. debate (宿主端本地)  │
 │  analyst_prompt(news)──▶ Host LLM
 │  debater_prompt(analysis)──▶ Host LLM
 │  ... N 轮, 用户实时可见 ...
 │                         │
 │  3. submit_analysis     │
 │──── final_analysis ────▶│ (云端: writer + cards + publish)
 │◀─── final_copy + cards ─│
```

新增两个云端 MCP 工具：

1. **`retrieve_and_report`**：只执行 source_retriever + reporter 两步，返回 `evidence_bundle` + `news_content` + `source_stats`。对应 `workflow.py` 中 `source_retriever_node → reporter_node` 子图。
2. **`submit_analysis_result`**：接收宿主端 debate 完成后的 `final_analysis` + `debate_history` + 上下文，继续执行 writer_node → image_generator_node → xhs_publisher_node 子图。

向后兼容：`analyze_topic` 全包式工具保留不变，继续在云端执行完整 workflow（含 debate）。新工具是增量新增，不破坏现有契约。这使得不具备宿主端 debate 能力的客户端（如纯 HTTP 调用）仍可使用旧路径。

**理由**：
- debate 是整个 workflow 中 LLM 消耗最大的环节（2-4 轮 analyst + debater 调用），迁移后云端 LLM 推理成本接近归零
- 宿主端 LLM 通常显著强于云端配置的 deepseek-chat（Claude Opus、GPT-4 等），debate 质量预期提升
- debate 过程从不透明的 SSE 事件流变为用户实时可见的对话输出，用户可以中途干预（"换个角度分析"）
- API 改动极小：拆分出两个新工具，复用现有 workflow 节点，不需要重写分析逻辑
- 不破坏"统一入口"模型：Gateway 仍是唯一入口，只是提供了更细粒度的工具拆分

### D4: skill 从纯流程文档升级为 debate 编排者

**选项 A**：skill 继续只做流程文档，不参与 debate 编排
- 与 D3 选项 A（debate 留云端）搭配

**选项 B（✅ 选定）**：skill 承担 debate 编排职责，成为宿主端 debate 的控制器
- skill 调用 `retrieve_and_report` 获取证据
- skill 指导宿主端 LLM 分别扮演 analyst 和 debater 角色执行多轮辩论
- skill 将最终分析结果通过 `submit_analysis_result` 交回云端
- skill 仍不需要声明机器可读的 MCP 绑定（远程 MCP Gateway 唯一即可）

**理由**：宿主端 skill 已经在做 5+ 步编排，增加 debate 循环只是增量变化。Skill 作为 debate 编排者的好处是用户完全看到辩论过程，且不需要新增任何本地服务或基础设施。

### D5: 云端状态存储必须拆成两类

1. **业务状态存储**：分析任务、结果、publish 记录、用户配置（推荐 Postgres）
2. **XHS 运行态存储**：xhs runtime 的账号/session/profile 数据（可先保留专用持久卷/SQLite，后续再抽象）

**理由**：XHS runtime 状态与普通业务数据的生命周期、访问模式和故障域不同，不应在本次设计中强行合并。

### D6: 多账号管理与租户隔离

云端部署面向多个 skill 使用者，每个用户必须拥有独立的空间和账号。代码审计发现当前系统有 **9 类全局单租户假设**需要消除：

#### 单租户瓶颈审计结果

| 组件 | 当前状态 | 多账号风险 |
|------|---------|-----------|
| `job_manager` | 全局单例，`_current_job_id` 全局唯一，一个用户跑任务阻塞所有人 | 用户互相阻塞 + 任务数据泄露 |
| `webhook_manager` | 全局单例，`_webhooks` 按 `job_id` 索引，无用户维度 | webhook 注册无归属 |
| `xiaohongshu_publisher` | 单例，`_login_session_id` 全局共享，cookies.json 全局共享 | 用户互踢登录态 |
| `user_settings.py` | 单个 `cache/user_settings.json`，无用户 key | 设置互相覆盖 |
| `workflow_status` | 全局 `_status` dict | 进度轮询看到别人的任务 |
| LLM keys | `.env` 全局 + `user_settings.json` 全局 + `KeyManager` 全局轮转 | 轮转状态互相干扰 |
| `outputs/` | 共享目录，含 markdown / card_previews / xhs_login / image_cache | 产物可被他人访问 |
| `cache/ai_daily/` | 全局共享，按日期 key | 如来源/模型不同会缓存污染 |
| API 鉴权 | 无任何 auth middleware | 任何人可访问所有端点 |

**选项 A（✅ 选定）**：Gateway 层引入 API key 鉴权 + 全栈 account_id 透传

实现策略：

```
┌──────────────────────────────────────────────────────┐
│  MCP Gateway (公网入口)                               │
│                                                       │
│  请求到达 → API key 验证 → 提取 account_id            │
│  → 注入到所有内部调用的 header/context                 │
├──────────────────────────────────────────────────────┤
│  内部服务                                             │
│                                                       │
│  job_manager:    jobs[account_id][job_id]             │
│  XHS publisher:  sessions[account_id]                 │
│  user_settings:  settings[account_id]                 │
│  outputs:        outputs/{account_id}/...             │
│  workflow_status: status[account_id]                  │
│  webhooks:       webhooks[account_id][job_id]         │
└──────────────────────────────────────────────────────┘
```

关键设计决策：

1. **身份识别**：Gateway 层通过 API key 识别调用方，映射到 `account_id`。API key 在用户首次注册 / 管理员分配时生成。
2. **任务隔离**：`job_manager` 从全局单例改为按 `account_id` 分区，每个用户有独立的任务队列和并发控制。
3. **XHS 账号隔离**：每个 `account_id` 拥有独立的 XHS 登录态（session、cookies、QR 流程）。**关键前提**：`shunl-xhs-mcp-integration` change 已将 XHS sidecar 切换为 ShunL12324/xhs-mcp（`@sillyl12324/xhs-mcp`），该方案**原生支持多账号**：
   - `xhs_add_account` 创建独立的登录 session，返回 `sessionId`
   - 所有操作可通过 `account` 参数指定账号
   - SQLite 持久化天然按账号隔离会话数据
   - 多账号池管理 + 并发保护已内置
   
   因此 XHS 多账号隔离无需从零设计，只需：将 `account_id` → ShunL 的 `account` 参数映射打通，在 `XiaohongshuPublisher` 适配层中将 Gateway 透传的 `account_id` 注入到每个 ShunL MCP 调用的 `account` 参数即可。参见 `openspec/changes/shunl-xhs-mcp-integration/` 中的适配层设计（D2）和工具名映射（shunl-xhs-mcp-adapter spec）。
4. **设置隔离**：`user_settings.json` 拆分为按 `account_id` 索引的存储（短期可用 `cache/user_settings/{account_id}.json`，后续迁移到数据库）。
5. **文件系统隔离**：`outputs/` 和 `cache/` 中的用户产物按 `account_id` 子目录隔离。AI Daily 采集缓存可保持全局共享（公共数据源、相同采集逻辑），但分析产物必须隔离。
6. **API 访问控制**：所有返回用户产物的端点（`/outputs`, `/card-previews`, `/xhs/login-qrcode/file/`）必须校验 `account_id` 归属。

**选项 B**：每用户独立部署一套完整服务栈
- 优点：隔离最彻底
- 缺点：运维成本随用户数线性增长，资源利用率极低

**理由**：共享服务 + 逻辑隔离在小到中等用户规模下是最佳平衡点。XHS sidecar（ShunL xhs-mcp）已原生支持多账号池管理和 SQLite 持久化隔离（参见 `shunl-xhs-mcp-integration` change），这大幅降低了 XHS 多账号的实现复杂度——只需在适配层透传 `account_id`，而非重新设计隔离架构。如果未来用户规模增长到需要物理隔离，可以在此架构上按 account 分片。

## Risks / Trade-offs

- **[宿主端 LLM 依赖]** → debate 质量取决于宿主端 LLM 能力；缓解：当前主要宿主端环境（OpenCode + Claude Opus/Sonnet、Cursor + GPT-4）均显著强于云端 deepseek-chat；对于不具备强 LLM 的客户端，保留 `analyze_topic` 全包式云端回退路径
- **[Skill 复杂度增加]** → skill 需要编排 debate 循环（~30 行逻辑）；缓解：debate 逻辑是纯 prompt 循环，无外部依赖，且 skill 已经在做同等复杂度的多步编排
- **[远程 MCP 成为单点入口]** → Gateway 故障会影响全部能力；缓解：健康检查、水平扩缩、内部服务超时隔离、灰度发布
- **[多账号改造面广]** → 9 类全局单例/共享状态需要全栈改造；缓解：以 `account_id` 透传为核心，逐层改造；AI Daily 采集缓存可保持全局共享减少工作量；短期可用文件系统隔离，后续迁移到数据库
- **[XHS 多账号复杂度]** → 每用户独立 XHS 登录态；缓解：ShunL xhs-mcp 原生支持多账号池管理（`xhs_add_account` + `account` 参数 + SQLite 隔离），无需额外架构设计，只需在适配层透传 `account_id` → ShunL `account` 参数（参见 `shunl-xhs-mcp-integration` change）
- **[两条路径维护成本]** → `analyze_topic`（全包云端）和 `retrieve_and_report` + `submit_analysis_result`（宿主端 debate）并行存在；缓解：两条路径共享相同的 workflow 节点，只是编排方式不同，代码重复极少
- **[skill 仍是文档型]** → 没有机器可读绑定时，某些执行器可能错误尝试 `skill_mcp`；缓解：远程 MCP Gateway 成为唯一入口后，这个问题显著弱化，后续再引入结构化 skill metadata

## Migration Plan

1. 保留当前本地四服务拓扑作为开发模式
2. 在云端部署等价四服务，但只对外暴露 `mcp gateway`
3. 将 `api`、`renderer`、`xhs runtime` 改为内网可达的私有服务
4. 拆分 `workflow.py`，新增 `retrieve_and_report` 和 `submit_analysis_result` 两个内部 API 端点
5. 在 MCP Gateway 层注册 `retrieve_and_report` 和 `submit_analysis_result` 两个新公共工具
6. 更新 skill 文档，增加宿主端 debate 编排逻辑（作为默认路径），保留 `analyze_topic` 全包式路径作为回退
7. 为 `mcp gateway` 增加 API key 鉴权中间件，实现 `account_id` 提取与透传
8. 改造 `job_manager` / `webhook_manager` / `workflow_status` 从全局单例改为按 `account_id` 分区
9. 改造 XHS 登录/发布链路支持按 `account_id` 隔离 session、cookies 和 QR 流程
10. 改造 `user_settings` 存储为按 `account_id` 索引
11. 改造 `outputs/` 和产物相关 API 为按 `account_id` 子目录隔离，增加归属校验
12. 将 skill 和用户文档中的默认运行环境改为"远程 MCP Gateway + API key"，本地 docker-compose 改成开发/自托管模式
13. 后续视需要评估计费系统和更细粒度的资源配额

## Open Questions

- 远程 MCP Gateway 的 API key 管理：自助注册 vs 管理员手动分配 vs 邀请码机制
- `retrieve_and_report` 返回的 `evidence_bundle` 体积可能较大（含全文抽取内容），是否需要分页或摘要模式
- 宿主端 debate 的 prompt（ANALYST_PROMPT / DEBATER_PROMPT）是硬编码在 skill 中还是通过 MCP 工具动态获取
- AI Daily 采集缓存是否保持全局共享（当前所有用户使用相同来源和采集逻辑），还是按账号隔离
- 账号级别的资源配额（并发任务数、每日分析次数、LLM 调用量）是否在本次实现
- 是否需要在 Gateway 层引入任务队列/异步 worker，以平滑多用户并发渲染负载
