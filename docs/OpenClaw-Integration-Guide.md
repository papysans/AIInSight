# AIInSight × OpenClaw 无痛接入指南

> 结论：AIInSight 的 MCP Server + Skill 体系与 OpenClaw 原生兼容，接入零代码改动，迁移工作量约 1-2 小时。

---

## 1. 架构兼容性总览

```
┌─────────────────────────────────────────────────────────┐
│                      OpenClaw Agent                      │
│  (Telegram / Discord / WhatsApp / Slack / ...)           │
│                                                          │
│  ┌────────────┐   ┌────────────────┐   ┌──────────────┐ │
│  │ LLM Driver │   │  Skill Engine  │   │  MCP Client  │ │
│  │ (Claude /   │   │  加载 SKILL.md │   │  连接外部     │ │
│  │  GPT / etc) │   │  → 指令执行    │   │  MCP Server  │ │
│  └──────┬─────┘   └───────┬────────┘   └──────┬───────┘ │
└─────────┼─────────────────┼────────────────────┼─────────┘
          │                 │                    │
          │           自然语言指令            JSON-RPC
          │           驱动工具调用               │
          │                 │                    │
          │                 ▼                    ▼
          │        ┌─────────────────────────────────┐
          │        │      AIInSight MCP Server        │
          │        │      (FastAPI :18061)             │
          │        │                                   │
          │        │  tools/list → 6 个工具自动注册     │
          │        │  tools/call → render / publish    │
          │        │                                   │
          │        │  ┌─────────┐    ┌──────────────┐ │
          │        │  │Renderer │    │  XHS MCP     │ │
          │        │  │ :3001   │    │  :18060      │ │
          │        │  └─────────┘    └──────────────┘ │
          │        └─────────────────────────────────┘
          │
     web_search / 内置能力
```

---

## 2. MCP Server 接入（零改动）

### 为什么无痛

| 维度 | AIInSight 现状 | OpenClaw 要求 | 兼容性 |
|------|---------------|--------------|--------|
| 协议 | JSON-RPC 2.0 | JSON-RPC 2.0 | 完全兼容 |
| 传输层 | SSE + POST (`/sse`, `/mcp`) | SSE 或 Streamable HTTP | 完全兼容 |
| 工具发现 | `tools/list` 返回 6 个工具 | 标准 `tools/list` | 自动注册 |
| 认证 | API Key via `X-API-Key` header（可选） | 支持自定义 headers | 完全兼容 |
| Protocol Version | `2024-11-05` | 兼容 | 完全兼容 |

### OpenClaw 侧配置

**本地开发**（同机 / 同 Docker 网络）：

```json
// openclaw.json 或 OpenClaw 配置文件
{
  "mcpServers": {
    "aiinsight": {
      "url": "http://localhost:18061/mcp"
    }
  }
}
```

**远程 / 云端部署**：

```json
{
  "mcpServers": {
    "aiinsight": {
      "url": "https://your-domain.com/mcp",
      "headers": {
        "X-API-Key": "your-api-key-here"
      }
    }
  }
}
```

配置完成后，OpenClaw 自动执行 `tools/list`，以下 6 个工具即对 agent 可用：

| 工具名 | 功能 |
|--------|------|
| `render_cards` | 渲染可视化卡片（title / daily_rank / impact 等） |
| `publish_xhs_note` | 发布小红书图文笔记 |
| `check_xhs_status` | 检查小红书登录状态 |
| `get_xhs_login_qrcode` | 获取小红书登录二维码 |
| `check_xhs_login_session` | 轮询扫码登录状态 |
| `submit_xhs_verification` | 提交短信验证码 |

---

## 3. Skill 迁移（改 frontmatter 即可）

### 格式对比

AIInSight 的 Skill 已采用 `SKILL.md` 格式（YAML frontmatter + Markdown 正文），与 OpenClaw 的 Skill 格式本质相同。

**现有格式**（`.agents/skills/ai-insight/SKILL.md`）：

```yaml
---
name: ai-insight
description: AI 日报助手 - 通过 web search 采集 AI 领域热点...
requires:
  - web_search
  - mcp_gateway
---
```

**OpenClaw 格式**（调整 `requires` 字段）：

```yaml
---
name: ai-insight
description: AI 日报助手 - 通过 web search 采集 AI 领域热点...
requires:
  tools:
    - web_search
  mcpServers:
    - aiinsight
---
```

### 迁移清单

| 步骤 | 内容 | 工作量 |
|------|------|--------|
| 1 | 复制 `.agents/skills/*` 到 OpenClaw 的 `skills/` 目录 | 1 分钟 |
| 2 | 调整每个 SKILL.md 的 `requires` 字段格式 | 5 分钟 |
| 3 | 确认 `web_search` 在 OpenClaw 中的可用性 | 见下方说明 |
| 4 | 验证 Skill 端到端执行 | 30 分钟 |

### Skill 正文（Markdown 指令）：零改动

Skill 正文里的工具调用指令如 "调用 `render_cards`"、"调用 `publish_xhs_note`" **不需要改**。OpenClaw 的 MCP 工具注册后，agent 通过 function calling 调用，与 Claude Code 的机制一致。

### 涉及的 Skill 文件

```
.agents/skills/
├── ai-insight/SKILL.md          → 日报采集 4 阶段 Pipeline
├── ai-topic-analyzer/SKILL.md   → 话题深度分析 5 阶段引擎
└── shared/GUIDELINES.md         → 共享渲染/发布规范
```

---

## 4. `web_search` 依赖处理

AIInSight 的两个核心 Skill 都依赖 `web_search` 能力。在 Claude Code 中这是内置能力，在 OpenClaw 中需要确认来源：

| 方案 | 说明 |
|------|------|
| **LLM 内置** | 如果 OpenClaw 使用 Claude（Anthropic），Claude 自带 web search |
| **MCP Server** | 配置 Exa / Tavily / SerpAPI 等 web search MCP server |
| **OpenClaw 插件** | 安装社区 web-search 插件 |

推荐：若 LLM 选 Claude，无需额外配置；若选其他 LLM，增加一个 web search MCP server。

---

## 5. 注意事项与风险

### 低风险

- **Tool description 质量**：OpenClaw agent 靠 tool description 决定何时调用工具。当前 6 个工具的描述已足够清晰，可按需微调以提升命中率。
- **网络连通性**：确保 OpenClaw 实例可以访问 AIInSight MCP Server（本地或公网）。

### 中风险

- **LLM 差异**：Skill 正文为 Claude 优化。若 OpenClaw 使用非 Claude LLM（GPT / Gemini），复杂 Skill（如 ai-topic-analyzer 的 5 阶段引擎）的执行质量可能有偏差，需实测验证。
  - Phase 分步控制可能需要更明确的 stop/continue 指令
  - 评分逻辑（scoring rubric）在不同 LLM 上表现不同
  - `{current_year}` 变量替换需确认 OpenClaw 是否支持

### 安全提醒

- OpenClaw 社区曾发生 ClawHavoc 恶意 Skill 事件（2026-01），自托管场景下只加载自己的 Skill，不从 ClawHub 安装未审查的第三方 Skill。
- 启用 API Key 认证（`OPINION_REQUIRE_API_KEY=true`），避免 MCP Server 裸奔。

---

## 6. 快速验证流程

```bash
# 1. 启动 AIInSight MCP Server
docker compose up -d

# 2. 验证 MCP Server 可达
curl http://localhost:18061/health

# 3. 验证 tools/list
curl -X POST http://localhost:18061/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'

# 4. 在 OpenClaw 配置中添加 aiinsight MCP server（见第 2 节）

# 5. 复制 Skill 到 OpenClaw
cp -r .agents/skills/* ~/.openclaw/workspace/skills/

# 6. 调整 SKILL.md frontmatter（见第 3 节）

# 7. 在 OpenClaw 中测试
#    发送 "AI日报" → 应触发 ai-insight Skill → 调用 web_search + render_cards
```

---

## 7. 总结

| 模块 | 迁移难度 | 改动量 | 说明 |
|------|---------|--------|------|
| MCP Server | 无痛 | 0 行代码 | 标准协议，配置即用 |
| Skill 文件 | 无痛 | 改 frontmatter | 格式几乎相同 |
| web_search 依赖 | 低 | 视 LLM 而定 | Claude = 零配置，其他 LLM 加 MCP |
| 端到端执行质量 | 需验证 | 0 行代码 | 取决于 LLM 选型 |

**一句话：接入 OpenClaw 是配置问题，不是开发问题。**
