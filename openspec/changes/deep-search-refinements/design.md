## Context

Deep Search + Smart Synthesis 已替代 Crucible 多轮辩论（见 `deep-search-smart-synthesis` change）。技术分析揭示 4 个可渐进式优化点，均为小范围文本修改，不涉及架构变更。

**约束**：改动仅限 SKILL.md 和 GUIDELINES.md 中的 prompt 文本和规则表格。

## Goals / Non-Goals

**Goals:**
- 置信度信号精度提升（4 档替代 3 档）
- Deep Search arXiv 搜索避免返回陈旧论文
- Smart Synthesis 在证据不足时输出明确的降级标注
- deep 模式搜索失败时优雅降级

**Non-Goals:**
- 不增加新 Phase 或数据源
- 不改变 analysis_packet schema
- 不涉及 MCP 工具或后端变更

## Decisions

### Decision 1: 置信度细分为 4 档

将 0.5-0.79 拆分为两档（0.5-0.64 / 0.65-0.79），区分依据为维度覆盖度（1 维度 vs 2 维度）。

**理由**：原 3 档设计中，"覆盖 1 个维度" 和 "覆盖 2 个维度" 被归为同一置信度区间，信号模糊。

### Decision 2: 降级指令嵌入 prompt 而非后处理

在 Smart Synthesis prompt 中直接添加"证据不足时标注"指令，而非在输出后做正则匹配添加。

**理由**：prompt 内嵌更可靠，LLM 能根据上下文自然整合降级标注，避免机械拼接。

### Decision 3: Rate limit 降级用计数器而非超时

检测连续 2 次搜索失败即触发降级，而非设定总超时阈值。

**理由**：搜索延迟波动大，超时阈值难以调优；连续失败更准确反映 rate limit 状态。

## Risks / Trade-offs

**[Risk]** 置信度 4 档可能过于复杂，LLM 难以精确落入正确区间
→ **Mitigation**：规则表格明确，且 prompt 中已包含计算逻辑；worst case 退化为原 3 档精度

**[Risk]** arXiv 加 `{current_year}` 可能过滤掉年初发布但标注前一年的论文
→ **Accept**：边缘情况，Phase 1 Discovery 的通用搜索会补充覆盖
