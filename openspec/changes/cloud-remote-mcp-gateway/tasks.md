## 1. Gateway 与部署边界梳理

- [ ] 1.1 盘点当前 `api` / `mcp` / `renderer` / `xhs-mcp` 的公网入口、内网依赖和状态持久化要求
- [ ] 1.2 定义远程 MCP Gateway 的唯一公网域名、协议与鉴权入口（例如 `/mcp`、health、API key / token 方案）
- [ ] 1.3 设计云端内部网络拓扑，明确哪些服务只允许私网访问
- [ ] 1.4 设计云端持久化方案，区分业务状态存储与 XHS runtime 状态存储

## 2. 远程 MCP Gateway 实现

- [ ] 2.1 将 `opinion_mcp/server.py` 的公网职责收敛为单一远程 MCP Gateway 契约
- [ ] 2.2 校验并补齐 Gateway 暴露的公共工具集合，确保与现有 skill / 文档契约一致
- [ ] 2.3 在 Gateway 注册 `retrieve_and_report` 工具：定义 inputSchema（topic, source_groups, source_names, depth），对接内部 API
- [ ] 2.4 在 Gateway 注册 `submit_analysis_result` 工具：定义 inputSchema（topic, news_content, final_analysis, debate_history, source_stats, image_count），对接内部 API
- [ ] 2.5 为远程 MCP Gateway 增加生产级 health / readiness / error surface
- [ ] 2.6 为远程 MCP Gateway 增加鉴权、限流与审计日志的实现入口

## 3. 内部服务云端化

- [ ] 3.1 将 `api` 服务改造为云端内部服务，禁止默认作为终端用户直接入口
- [ ] 3.2 将 `renderer` 服务改造为云端内部渲染服务，确认卡片生成路径只通过内部调用触发
- [ ] 3.3 将 `xhs-mcp` 改造为云端内部 XHS runtime，确认登录、二维码与发布链路仅通过内部服务访问
- [ ] 3.4 把本地 `docker compose` 明确降级为开发 / 自托管拓扑，不再作为终端用户默认路径

## 4. Skill 与文档对齐

- [ ] 4.1 更新 skill 与 README 中的默认运行假设，使其面向单一远程 MCP Gateway 而不是本地四容器栈
- [ ] 4.2 清理或降级所有要求用户理解本地端口、compose、sidecar 拓扑的公开使用说明
- [ ] 4.3 补充远程登录 / 发布说明，确保二维码登录、会话轮询、验证码提交都走统一远程入口
- [ ] 4.4 更新 `ai-topic-analyzer` skill，增加宿主端 debate 编排逻辑作为默认分析路径（详见 Section 5）

## 5. 宿主端 debate 实施

### 5.1 云端 API 拆分

- [ ] 5.1.1 在 `app/api/endpoints.py` 新增 `POST /api/retrieve-and-report` 端点：只执行 `source_retriever_node → reporter_node`，返回 `evidence_bundle` + `news_content` + `source_stats`
- [ ] 5.1.2 从 `app/services/workflow.py` 中提取 `source_retriever_node` + `reporter_node` 为可独立调用的子图或函数
- [ ] 5.1.3 在 `app/api/endpoints.py` 新增 `POST /api/submit-analysis-result` 端点：接收 `final_analysis` + `debate_history` + 上下文，继续执行 `writer_node → image_generator_node → xhs_publisher_node`
- [ ] 5.1.4 从 `app/services/workflow.py` 中提取 `writer_node` + 下游节点为可独立调用的子图或函数
- [ ] 5.1.5 确保 `POST /api/analyze`（全包式）不受影响，继续作为向后兼容路径

### 5.2 MCP 工具层实现

- [ ] 5.2.1 在 `opinion_mcp/tools/` 新增 `retrieve_and_report` 工具函数，调用内部 `POST /api/retrieve-and-report`
- [ ] 5.2.2 在 `opinion_mcp/tools/` 新增 `submit_analysis_result` 工具函数，调用内部 `POST /api/submit-analysis-result`
- [ ] 5.2.3 在 `opinion_mcp/server.py` 的 `MCP_TOOLS` 列表中注册两个新工具的 schema 定义
- [ ] 5.2.4 在 `opinion_mcp/services/backend_client.py` 新增对两个新内部 API 的 HTTP 调用方法

### 5.3 Skill 层 debate 编排

- [ ] 5.3.1 在 `ai-topic-analyzer` skill 中新增宿主端 debate 工作流描述：`retrieve_and_report` → 宿主端 analyst 角色 → 宿主端 debater 角色 → 循环判断 → `submit_analysis_result`
- [ ] 5.3.2 在 skill 中提供 analyst prompt 和 debater prompt 模板（源自 `workflow.py` 中的 `ANALYST_PROMPT` / `DEBATER_PROMPT`）
- [ ] 5.3.3 在 skill 中明确 debate 循环控制逻辑：debater 回复含 "PASS" 或达到 max_rounds 时结束
- [ ] 5.3.4 在 skill 中保留 `analyze_topic` 全包式路径作为回退选项（标注为"适用于不支持宿主端 debate 的客户端"）
- [ ] 5.3.5 更新 `ai-insight` skill 中 AI Daily 分析流程，使其默认使用宿主端 debate 路径

### 5.4 资源与约束

- [ ] 5.4.1 为 `retrieve_and_report` 设置超时约束（source retrieval 可能涉及多源网络请求）
- [ ] 5.4.2 为 `submit_analysis_result` 的 writer + image_generator 设置超时约束
- [ ] 5.4.3 确认 `evidence_bundle` 返回体积在合理范围内（必要时提供摘要模式选项）

## 6. 迁移与验证

- [ ] 6.1 部署一套云端等价拓扑（Gateway + api + renderer + xhs runtime + persistence）并验证服务连通
- [ ] 6.2 验证宿主端 debate 完整链路：`retrieve_and_report` → 宿主端 debate → `submit_analysis_result` → 文案 + 卡片输出
- [ ] 6.3 验证 `analyze_topic` 全包式云端回退路径仍正常工作
- [ ] 6.4 验证远程 XHS 登录链路：`check_xhs_status` → `get_xhs_login_qrcode` → `check_xhs_login_session` → `submit_xhs_verification`
- [ ] 6.5 验证渲染与发布链路仍通过云端内部服务完成，不要求用户运行本地 Docker
- [ ] 6.6 对比宿主端 debate vs 云端全包式 debate 的输出质量（至少 3 个话题样本）
- [ ] 6.7 补充 rollback / fallback 方案：远程 Gateway 不可用时如何回退到开发或自托管模式

## 7. 多账号管理与租户隔离

### 7.1 身份与鉴权

- [ ] 7.1.1 设计 API key 数据模型：`api_key` → `account_id` 映射，含创建时间、状态（active/revoked）、备注
- [ ] 7.1.2 在 `opinion_mcp/server.py` MCP Gateway 层实现 API key 鉴权中间件：从请求 header 提取 key → 验证 → 注入 `account_id` 到请求上下文
- [ ] 7.1.3 在 `app/main.py` FastAPI 后端增加内部鉴权：从 Gateway 转发的 header 中提取 `account_id`，注入到所有 endpoint handler
- [ ] 7.1.4 实现 API key 管理接口（仅运维用）：创建 key、列出 key、吊销 key

### 7.2 任务隔离

- [ ] 7.2.1 改造 `opinion_mcp/services/job_manager.py`：`_jobs` 按 `account_id` 分区，`_current_job_id` 改为按 `account_id` 索引的并发控制
- [ ] 7.2.2 改造 `opinion_mcp/tools/analyze.py`：`analyze_topic` / `get_analysis_status` / `get_analysis_result` 传入 `account_id`，所有查询按 `account_id` 过滤
- [ ] 7.2.3 改造 `opinion_mcp/services/webhook_manager.py`：webhook 注册关联 `account_id`，推送时校验归属
- [ ] 7.2.4 改造 `app/services/workflow_status.py`：`_status` 按 `account_id` 分区

### 7.3 XHS 账号隔离（基于 ShunL xhs-mcp 原生多账号能力）

- [ ] 7.3.1 在 `XiaohongshuPublisher` 适配层中，将 Gateway 透传的 `account_id` 映射为 ShunL MCP 调用的 `account` 参数（`xhs_add_account`、`xhs_publish_content`、`xhs_check_auth_status` 等均支持 `account` 参数）
- [ ] 7.3.2 改造 `XiaohongshuPublisher` 的 `_login_session_id` 从全局单值改为按 `account_id` 索引的 dict，确保 QR/验证码流程按用户隔离
- [ ] 7.3.3 改造 QR 码输出路径为按 `account_id` 隔离：`outputs/xhs_login/{account_id}/`，消除全局 `latest.json`
- [ ] 7.3.4 验证 ShunL xhs-mcp sidecar 的 SQLite 多账号持久化在 Docker volume 重启后正常保持各用户独立 session

### 7.4 设置与凭证隔离

- [ ] 7.4.1 改造 `app/services/user_settings.py`：从单个 `cache/user_settings.json` 改为按 `account_id` 索引（如 `cache/user_settings/{account_id}.json`）
- [ ] 7.4.2 改造 `app/llm.py` 的 `KeyManager` 和 `get_agent_llm`：per-account key rotation state，支持 account 级别的 provider/model 覆盖
- [ ] 7.4.3 改造 `app/services/image_generator.py`：Volcengine 凭证按 account 查找

### 7.5 文件系统隔离

- [ ] 7.5.1 改造 `app/services/workflow.py` 的 `writer_node`：markdown 输出到 `outputs/{account_id}/`
- [ ] 7.5.2 改造 `app/services/card_render_client.py`：卡片预览保存到 `outputs/{account_id}/card_previews/`
- [ ] 7.5.3 改造 `opinion_mcp/utils/url_validator.py`：image cache 按 `account_id` 或全局共享（图片缓存无隐私风险时可保持全局）
- [ ] 7.5.4 改造 `app/api/endpoints.py` 中所有产物服务端点（`/outputs`, `/card-previews/{filename}`, `/xhs/login-qrcode/file/{filename}`）：增加 `account_id` 归属校验

### 7.6 缓存策略

- [ ] 7.6.1 确认 AI Daily 采集缓存（`cache/ai_daily/`）保持全局共享的合理性（公共数据源、统一采集逻辑）
- [ ] 7.6.2 如有来源/模型按账号差异化的需求，设计缓存 key 加入 `account_id` 维度的方案

### 7.7 验证

- [ ] 7.7.1 验证两个不同 API key 的用户可以并行执行分析任务互不阻塞
- [ ] 7.7.2 验证用户 A 无法通过 API 访问用户 B 的任务状态、分析结果和产物文件
- [ ] 7.7.3 验证用户 A 的 XHS 登录/重置操作不影响用户 B 的 XHS session
- [ ] 7.7.4 验证用户 A 的 LLM key 配置不影响用户 B 的分析调用
