## Why

当前 AIInSight 的主能力依赖本地 `docker compose` 四服务栈（`api` / `mcp` / `renderer` / `xhs-mcp`），用户必须理解端口、容器状态和服务边界，才能稳定使用技能链路。这与“用户只安装/使用一个 skill，其余能力全部托管在云端”的目标不符，也让技能执行器难以自动判断该连接哪个服务入口。

现在已经具备推进云端化的关键前提：`opinion_mcp` 已经提供统一的 MCP / HTTP tool surface，`xhs-mcp` 的登录与持久化链路已经验证通过，渲染与发布都已拆成独立服务。因此适合引入“单一远程 MCP Gateway + 内部服务”的架构，把用户侧体验收敛为“只用 skill + 一个远程 MCP 入口”。

## What Changes

- **新增** 云端单一远程 MCP Gateway 方案，对外只暴露一个远程 MCP 入口，统一承载 `analyze_topic`、`publish_to_xhs`、`check_xhs_status` 等工具
- **新增** 服务边界设计：`api`、`renderer`、`xhs-mcp` 改为云端内部服务，不再要求终端用户本地运行 `docker compose`
- **新增** 远程部署拓扑与运行时约束，包括内部服务通信、状态持久化、对象存储与认证边界
- **新增** 技能运行模型约束：skill 只负责交互和流程说明，不再假设本地四容器栈
- **明确决策** 多轮 Agent 辩论（`analyst → debater` 循环）迁移到宿主端执行：宿主端（OpenCode / Claude Code 等 AI Agent 环境）天生具备 LLM 推理和多步编排能力，debate 作为纯 LLM prompt 循环无需云端基础设施依赖，迁移后可消除云端 LLM 推理成本、提升 debate 质量（宿主端模型通常更强）、并让用户实时可见每轮辩论过程
- **新增** 云端新增 `retrieve_and_report` 工具：只执行 source retrieval + reporter，返回 evidence_bundle 和 news_content 供宿主端 debate 消费
- **新增** 云端新增 `submit_analysis_result` 工具：接收宿主端 debate 完成后的 final_analysis，继续执行 writer + card generation + publish 链路
- **新增** 多账号管理与租户隔离：云端部署面向多个 skill 使用者，每个用户拥有独立的 XHS 账号状态、任务空间、输出目录和设置，互不干扰。XHS 多账号隔离基于 `shunl-xhs-mcp-integration` change 引入的 ShunL xhs-mcp 原生多账号能力（`account` 参数 + SQLite 隔离）
- **新增** Gateway 鉴权层：通过 API key / token 识别调用方身份，将请求路由到对应用户的隔离空间
- **修改** 现有 Docker-first XHS 运行时规范，使其适配"云端内部 sidecar"而非"终端用户本地 compose"语义，并支持多用户 XHS 账号隔离
- **修改** 现有 AI 话题分析能力规范，明确云端负责 source retrieval / reporter / writer / card generation / publish，debate 由宿主端负责

## Capabilities

### New Capabilities
- `remote-mcp-gateway`: 统一对外暴露的远程 MCP 入口，负责聚合分析、渲染、XHS 登录与发布能力
- `cloud-service-topology`: 云端内部服务拓扑与运行时边界，包括 api / renderer / xhs-mcp / persistence / object storage 的职责划分
- `multi-account-management`: 多账号管理与租户隔离，每个 skill 使用者拥有独立的 XHS 登录态、任务队列、输出空间和用户设置

### Modified Capabilities
- `docker-first-official-xhs-runtime`: 从"本地 Docker sidecar 是默认运行方式"调整为"云端内部 XHS runtime 是默认支持拓扑"
- `ai-daily-topic-analysis`: AI 话题分析链路拆分为云端（retrieval + reporter + writer + cards + publish）和宿主端（analyst + debater debate 循环）两段协作执行
- `mcp-tool-schema-compatibility`: 远程 MCP Gateway 作为对外唯一工具契约入口，新增 `retrieve_and_report` / `submit_analysis_result` 工具以支持宿主端 debate 模式

## Impact

- **受影响系统**: `opinion_mcp/server.py`（云端 MCP Gateway 角色，新增 `retrieve_and_report` / `submit_analysis_result` 工具，新增鉴权中间件）、`opinion_mcp/services/job_manager.py`（从全局单例改为按用户隔离）、`app/services/xiaohongshu_publisher.py`（XHS 登录态按用户隔离）、`app/services/user_settings.py`（设置按用户隔离）、`app/api/endpoints.py`（内部分析/发布 API，新增拆分端点）、`app/services/workflow.py`（拆分为 retrieval+reporter 前段和 writer+publish 后段）、`renderer`、`xhs-mcp`、部署配置、skill 文档
- **受影响运行方式**: 从"用户本地 docker-compose"迁移到"用户只连远程 MCP endpoint + API key，内部服务云端托管"；debate 从云端 workflow 迁移到宿主端 skill/assistant 层执行；每个用户拥有独立的任务空间和 XHS 账号
- **受影响产品体验**: 用户侧配置从多个容器/端口简化为一个远程 MCP 入口 + 一个 API key；debate 过程从黑盒轮询变为用户实时可见、可干预；多用户共用云端实例互不干扰
- **主要取舍**: 云端服务更轻（消除 debate LLM 推理成本），宿主端 skill 复杂度略增（需编排 debate 循环）；多账号隔离增加云端复杂度，但是多用户云端部署的必备前提；`analyze_topic` 全包式调用仍作为向后兼容路径保留
