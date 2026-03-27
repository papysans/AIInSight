## Why

Deep Search + Smart Synthesis 架构已落地，但技术分析揭示了 4 个可渐进式优化的点：置信度中间区间过宽（0.5-0.79 覆盖面太广）、arXiv 搜索缺少时间限定（返回陈旧论文）、Smart Synthesis 缺少证据不足时的降级指令、deep 模式总搜索量 15-18 次可能触发 rate limit 但无降级预案。

## What Changes

- **置信度中间区间细分**：将 0.5-0.79 拆为两档（0.5-0.64 / 0.65-0.79），提升置信度信号精度
- **arXiv 搜索加时间限定**：Deep Search 中 arXiv 搜索语法追加 `{current_year}`
- **证据不足降级指令**：Smart Synthesis prompt 增加"High 可信度 <3 条时，明确标注证据有限"
- **deep 模式 rate limit 降级预案**：连续搜索返回错误时自动降级为 standard 搜索量

## Capabilities

### New Capabilities

_(无新增能力)_

### Modified Capabilities

- `ai-daily-topic-analysis`: 置信度评估细化、Deep Search arXiv 时间限定、Smart Synthesis 降级指令、deep 模式 rate limit 降级

## Impact

**代码变更**:
- `.agents/skills/ai-topic-analyzer/SKILL.md` — Phase 2.5 搜索语法、Phase 3 prompt、置信度规则、deep 模式降级逻辑
- `.agents/skills/shared/GUIDELINES.md` — Section 6 置信度规则细分、Section 4.4 arXiv 搜索语法
