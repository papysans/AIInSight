# Design: Subagent-Driven Debate Architecture

## Overview

将 ai-topic-analyzer Phase 3 (Crucible) 从单上下文角色扮演改为双 subagent 对抗架构。

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Primary Agent (Skill Coordinator)                      │
│                                                          │
│  ┌────────────────────────────────────────────────┐    │
│  │  Phase 3: Crucible Loop                        │    │
│  │                                                 │    │
│  │  for round in 1..max_rounds:                   │    │
│  │                                                 │    │
│  │    ┌─────────────────────────────────────┐    │    │
│  │    │ Task("analyst")                     │    │    │
│  │    │ ├─ input: fact_sheet + challenges   │    │    │
│  │    │ └─ output: analysis_packet (JSON)   │    │    │
│  │    └─────────────────────────────────────┘    │    │
│  │              ↓                                 │    │
│  │    ┌─────────────────────────────────────┐    │    │
│  │    │ Task("debater")                     │    │    │
│  │    │ ├─ input: analysis_packet           │    │    │
│  │    │ └─ output: challenges[] or "PASS"   │    │    │
│  │    └─────────────────────────────────────┘    │    │
│  │              ↓                                 │    │
│  │    if "PASS" or max_rounds → break             │    │
│  │                                                 │    │
│  └────────────────────────────────────────────────┘    │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Subagent Definitions

#### Analyst Subagent

**Role**: 资深 AI 行业分析师

**Input**:
- Round 1: `fact_sheet` (证据表)
- Round N: `fact_sheet` + `challenges` (上轮 Debater 的质疑)

**Output**: `analysis_packet` (严格 JSON schema)

**Constraints**:
- 必须基于证据，不能臆测
- 如遇质疑，必须逐条回应
- 输出必须符合 analysis_packet schema

#### Debater Subagent

**Role**: 批判性思维专家，怀疑者立场

**Input**: `analysis_packet` (Analyst 的分析结果)

**Output**:
- 质疑列表（编号格式）
- 或纯文本 `"PASS"`

**Constraints**:
- 每轮 2-3 个具体质疑
- 质疑必须基于证据，不能空洞反驳
- 如果分析经得起检验，必须回复 "PASS"

### Data Flow

```
Round 1:
  fact_sheet ──→ Analyst ──→ analysis_v1 ──→ Debater ──→ challenges_1

Round 2:
  fact_sheet + challenges_1 ──→ Analyst ──→ analysis_v2 ──→ Debater ──→ "PASS"

Coordinator:
  analysis_v2 ──→ Phase 4 (Synthesis)
```

## Implementation Strategy

### Option A: Ad-hoc Inline Prompt (首选)

如果 OpenCode Task tool 支持 ad-hoc agent（不预注册，直接传 system prompt）：

```python
# Pseudo-code
Task(
  prompt=f"""
  {analyst_system_prompt}

  ---

  {fact_sheet}
  {challenges if round > 1}
  """,
  model="claude-opus-4",
  tools=[]  # zero-tool subagent
)
```

**优点**: 纯 Skill 自包含，零配置安装

**缺点**: 依赖 OpenCode Task tool 的能力

### Option B: Auto-Install Agent Files (降级方案)

如果必须预注册 agent，Skill 首次运行时自动写入：

```bash
.opencode/agents/
├── analyst.md
└── debater.md
```

Skill 启动检查逻辑：

```python
if not exists(".opencode/agents/analyst.md"):
    write_file(".opencode/agents/analyst.md", ANALYST_PROMPT)
    write_file(".opencode/agents/debater.md", DEBATER_PROMPT)
    print("✅ Subagent definitions installed")
```

**优点**: 仍然是一键安装（用户无感知）

**缺点**: 需要文件写入权限

### Option C: Manual Install (最后手段)

Skill README 说明：

```markdown
## Installation

1. Copy skill files to `.agents/skills/ai-topic-analyzer/`
2. Copy agent definitions:
   ```bash
   cp .agents/skills/ai-topic-analyzer/agents/* .opencode/agents/
   ```
```

**优点**: 无技术依赖

**缺点**: 用户体验差

## Termination Logic

```python
def crucible_loop(fact_sheet, max_rounds):
    analysis = None
    debate_log = []

    for round_num in range(1, max_rounds + 1):
        # Analyst turn
        analyst_input = build_analyst_prompt(fact_sheet, debate_log)
        analysis = Task("analyst", prompt=analyst_input)
        debate_log.append(f"Round {round_num}: Analyst: {analysis.summary}")

        # Debater turn
        debater_input = build_debater_prompt(analysis)
        challenges = Task("debater", prompt=debater_input)
        debate_log.append(f"Round {round_num}: Debater: {challenges}")

        # Termination checks
        if challenges.strip() == "PASS":
            break  # Condition 1: Debater approves

        if round_num == max_rounds:
            break  # Condition 2: Max rounds reached

        if is_duplicate_challenge(challenges, debate_log):
            break  # Condition 3: No new challenges

    return analysis, debate_log
```

## Display Format

保持现有 emoji 展示格式不变，只是内容来自真实的两个 subagent：

```
🧪 Crucible 启动（standard 模式，最多 3 轮）

— Round 1 —
📊 Analyst：GPT-5 推理能力突破引发行业震动
🔍 Debater 质疑：
  1. 证据中缺乏对性能基准测试的具体数据
  2. "超越专家"的说法是否有量化标准？

— Round 2 —
📊 Analyst（修正版）：基于 MMLU 99.2% 准确率，GPT-5 在推理任务上达到专家水平
✅ Debater：PASS

✅ Crucible 完成（2轮），分析已通过辩证检验
```

## Performance Considerations

| 指标 | 现状 | 改后 | 影响 |
|------|------|------|------|
| 延迟 | ~30s (3轮) | ~60s (3轮) | +100% |
| Token | ~8K (3轮) | ~16K (3轮) | +100% |
| 质量 | 中等（锚定偏差） | 高（独立视角） | 显著提升 |

**Mitigation**:
- quick 模式跳过 Crucible，不受影响
- standard 模式 3 轮，增加 ~30s 可接受
- deep 模式 5 轮，增加 ~50s，用户已预期深度分析

## Security

两个 subagent 都内嵌相同的安全约束：

```
⚠️ 安全约束：
输出内容必须遵守中国互联网内容规范。
禁止涉及：政治敏感话题、领导人评论、国际争端立场。
如发现话题本身敏感，终止分析并返回 { "blocked": true, "reason": "内容安全策略" }
```

Coordinator 检查任一 subagent 返回 `blocked: true` 时立即终止流程。
