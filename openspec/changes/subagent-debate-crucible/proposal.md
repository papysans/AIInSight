# Proposal: Subagent-Driven Debate for Crucible Phase

## Problem

当前 ai-topic-analyzer 的 Phase 3 (Crucible) 在同一个 LLM 上下文窗口内模拟 Analyst 和 Debater 两个角色。这导致：

1. **锚定偏差** — 模型刚生成 Analyst 的分析，紧接着要"真诚地"反驳自己，天然倾向于温和质疑
2. **信息泄漏** — Debater 能看到 Analyst 的完整推理链（包括内心独白），无法做到真正的信息隔离
3. **角色坍缩** — 随着轮次增加，两个 persona 趋于融合，Debater 越来越像在"帮 Analyst 改进"而非"挑战 Analyst"
4. **观感不佳** — 用户看到的是一个 AI 自说自话，而非两个独立视角的真实交锋

## Solution

利用 OpenCode 的 subagent 机制（Task tool），将 Analyst 和 Debater 拆分为两个独立 subagent，每轮 debate 在独立 session 中执行。

### 核心约束：Skill 自包含

**用户只需安装 Skill 文件即可运行，不需要额外配置 `opencode.json` 或手动注册 agent。**

这要求 Skill 在执行时通过 Task tool 的 inline prompt 方式调用 subagent，而非依赖预注册的 named agent。如果 OpenCode 的 Task tool 不支持 ad-hoc inline prompt（即必须预注册 agent 才能调用），则需要：

- **方案 A（首选）**：Skill 首次运行时自动写入 `.opencode/agents/analyst.md` + `debater.md`，作为 Skill install 的一部分
- **方案 B（降级）**：Skill 包内附带 agent 定义文件，README 说明需要复制到 `.opencode/agents/`

### 架构

```
Primary Agent (Skill 执行者 / Coordinator)
│
│  Phase 3: Crucible
│
│  Round N:
│  ├── Task("analyst") ──→ 独立 session
│  │   input:  fact_sheet + 上轮质疑（如有）
│  │   output: analysis_packet (JSON)
│  │
│  ├── Task("debater") ──→ 独立 session
│  │   input:  analysis_packet
│  │   output: 质疑列表 or "PASS"
│  │
│  └── Coordinator 判断终止条件
│      ├── "PASS" → 进入 Phase 4
│      ├── max_rounds → 取最新版本，进入 Phase 4
│      └── 否则 → Round N+1
```

### 与现状的对比

| 维度 | 现在（同上下文角色扮演） | 改后（Subagent 对抗） |
|------|----------------------|---------------------|
| 上下文 | 1 个共享上下文 | 每轮 2 个独立上下文 |
| 信息隔离 | 无，Debater 看到 Analyst 全部推理 | 完全隔离，只传递结构化输出 |
| 锚定偏差 | 强，模型倾向于不反驳自己 | 弱，独立 session 无历史锚定 |
| 模型多样性 | 不可能 | 可选，debater 可配不同 model |
| 展示效果 | 一个 AI 自说自话 | 两个独立 agent 的真实交锋结果 |
| Token 开销 | 1x | ~2x（每轮两个独立 session） |
| 用户体验 | 不变 | 展示格式不变，内容质量提升 |

## Scope

### In Scope

- 定义 `analyst` 和 `debater` 两个 subagent（prompt + 配置）
- 修改 SKILL.md Phase 3 的执行方式：从同上下文角色扮演改为 Task tool 调度
- 修改 GUIDELINES.md Section 6 (Debate 终止条件) 适配 subagent 模式
- 保持用户可见展示格式不变

### Out of Scope

- Phase 1/2/4/5 不变
- 不引入 Agent Teams（overkill for this use case）
- 不引入跨模型 debate（保持单 CLI 自包含）
- 不改变 analysis_packet schema

## Risks

| 风险 | 影响 | 缓解 |
|------|------|------|
| OpenCode Task tool 不支持 ad-hoc inline prompt | 无法做到纯 Skill 自包含 | 降级到方案 A（自动写入 agent 文件）或方案 B（手动安装） |
| Subagent 冷启动延迟 | 每轮 debate 增加 ~10-15s | 3 轮 debate 总增加 ~30-45s，可接受 |
| Token 开销翻倍 | 成本增加 | standard 模式 3 轮 = 6 次 subagent 调用，deep 模式 5 轮 = 10 次；quick 模式跳过 Crucible 不受影响 |
| Subagent 输出格式不稳定 | Coordinator 解析失败 | Analyst prompt 强制 JSON schema；Debater prompt 强制 "PASS" 或编号列表格式 |

## Open Questions

1. **OpenCode Task tool 是否支持 ad-hoc agent？** 即不预注册 agent name，直接在 Task 调用时传入完整 system prompt + model 配置。这决定了"零配置安装"是否可行。

2. **Subagent 的 tool 权限如何控制？** Analyst 和 Debater 都不需要任何工具（不需要读写文件、不需要 bash、不需要 web search），理想情况下应该是 zero-tool subagent，只做纯推理。

3. **是否值得让 Debater 用不同 model？** 比如主模型用 Claude，Debater 用 Gemini。这能最大化认知多样性，但增加了配置复杂度，且破坏了"单 CLI 自包含"原则。建议作为可选配置，不作为默认行为。
