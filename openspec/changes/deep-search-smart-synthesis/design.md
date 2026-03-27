## Context

当前 ai-topic-analyzer 使用 5 阶段流程：Discovery → Evidence → Crucible → Synthesis → Delivery。

**现状问题**：
- Phase 3 (Crucible) 使用 3-5 轮 Analyst ↔ Debater 辩论，增加 30-60s 延迟
- Phase 1 (Discovery) 的通用 web search 覆盖度有限，可能遗漏垂直数据源的深度内容
- 热点分析场景更看重"快速"和"有料"，而非"学术严谨"

**约束**：
- 必须保持 Skill 自包含（零后端 LLM 依赖）
- 必须兼容 quick/standard/deep 三种模式
- 输出格式（analysis_packet + xhs_copy）不变

## Goals / Non-Goals

**Goals:**
- 用 Deep Search + Smart Synthesis 替代多轮辩论，提升速度和证据深度
- 针对热点从垂直数据源（AIBase、机器之心、arXiv、GitHub Trending）深度检索
- 单轮生成高质量分析，prompt 内嵌批判性思维

**Non-Goals:**
- 不改变 Phase 1/2/4/5 的核心逻辑
- 不引入后端 LLM 服务
- 不改变 analysis_packet schema

## Decisions

### Decision 1: 新增 Phase 2.5 (Deep Search) 而非扩展 Phase 1

**选择**: 在 Evidence 和 Synthesis 之间插入独立的 Deep Search 阶段

**理由**:
- Phase 1 (Discovery) 是广度搜索（3 类 × 2 语言），Phase 2.5 是深度搜索（针对已识别热点）
- 分离关注点：Discovery 负责"找到热点"，Deep Search 负责"挖深细节"
- quick 模式可以跳过 Deep Search，保持快速路径

**备选方案**: 在 Phase 1 增加更多搜索轮次
- 缺点：所有模式都会变慢，无法按需深挖

### Decision 2: Deep Search 使用定向 site: 搜索而非 API 调用

**选择**: 使用 `site:aibase.com`、`site:jiqizhixin.com` 等定向搜索

**理由**:
- 保持 Skill 自包含，不依赖各数据源的专用 API
- Web Search 工具已支持 site: 语法
- 覆盖主流中英文 AI 媒体已足够

**备选方案**: 调用各数据源的 RSS/API
- 缺点：需要维护多个 API 集成，破坏 Skill 自包含原则

### Decision 3: Smart Synthesis 用单轮 prompt 而非 subagent 辩论

**选择**: 在 Synthesis prompt 中内嵌批判性思维指令

**理由**:
- 避免 subagent 的冷启动开销和复杂度
- 现代 LLM 已具备"自我质疑"能力，无需真实对抗
- 保持实现简单，易于调试

**备选方案**: 使用 subagent 实现真实对抗（见 subagent-debate-crucible change）
- 缺点：增加延迟和 token 开销，热点场景不值得

## Risks / Trade-offs

**[Risk]** Deep Search 可能返回低质量结果（广告、SEO 垃圾）
→ **Mitigation**: 在 Evidence 阶段已有可信度筛选（High/Medium/Low），Deep Search 结果同样经过筛选

**[Risk]** 单轮 Synthesis 质量不如多轮辩论
→ **Mitigation**: 通过 prompt 工程（内嵌反面证据、置信度自评）补偿；quick 模式已证明单轮可行

**[Trade-off]** 去掉 Crucible 后，用户看不到"辩论过程"
→ **Accept**: 用户更关心最终结果，Deep Search 的进度展示可以替代信任感建立

**[Risk]** Deep Search 增加的搜索次数可能触发 rate limit
→ **Mitigation**: standard 模式限制 Deep Search 为 3-5 次定向搜索；deep 模式才开启全量检索
