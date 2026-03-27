## Why

当前 ai-topic-analyzer 的 Phase 3 (Crucible) 使用多轮 Analyst ↔ Debater 辩论来提升分析质量，但在热点分析场景存在两个问题：

1. **时效性差** — 3-5 轮辩论增加 30-60s 延迟，而热点分析的核心价值是"快速抓住要点"
2. **证据深度不足** — Phase 1 (Discovery) 的通用 web search 可能遗漏各大数据源（AIBase、机器之心、arXiv、GitHub Trending）的深度内容

本 change 用 **Deep Search + Smart Synthesis** 替代多轮辩论：在合成前针对热点做深度检索，然后单轮生成高质量分析。

## What Changes

- **移除** Phase 3 (Crucible) 的多轮辩论循环
- **新增** Phase 2.5 (Deep Search) — 针对热点从各大数据源深度检索
- **改造** Phase 3 → Smart Synthesis — 单轮生成，prompt 内嵌批判性思维和证据强度感知
- **保留** quick 模式跳过 Deep Search 的能力

## Capabilities

### New Capabilities
- `deep-search-phase`: 针对热点话题从多个垂直数据源（AIBase、机器之心、TechCrunch、arXiv、GitHub Trending）执行深度检索，返回结构化证据包
- `smart-synthesis`: 基于证据质量的单轮分析合成，内嵌批判性思维，输出带置信度的 analysis_packet

### Modified Capabilities
- `ai-daily-topic-analysis`: Phase 流程从 Discovery → Evidence → Crucible → Synthesis 改为 Discovery → Evidence → Deep Search → Smart Synthesis

## Impact

**代码变更**:
- `.agents/skills/ai-topic-analyzer/SKILL.md` — Phase 3 重写，Phase 2.5 新增
- `.agents/skills/shared/GUIDELINES.md` — 更新 Section 4 (搜索策略) 和 Section 6 (终止条件 → 置信度评估)

**性能影响**:
- standard 模式：延迟从 ~90s 降至 ~60s（去掉辩论循环，增加深度检索）
- quick 模式：不受影响（跳过 Deep Search）

**用户体验**:
- 去掉 🧪 Crucible 的多轮展示
- 新增 🔎 Deep Search 进度展示
- 保持最终输出格式不变
