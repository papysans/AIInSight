# 2026-03-27 卡片形态调研

## 背景

当前单话题分析的展示内容，已经从“给一个结论”扩展成三类信息：

1. 结论本身：核心观点、置信度、行动建议
2. 证据基础：多来源事实、覆盖维度、可信度
3. 推演过程：质疑点、修正点、最终通过条件

现有卡片集合是：

- `title`
- `impact`
- `radar`
- `timeline`

这套组合更像“封面 + 摘要 + 图表 + 过程列表”，适合早期较轻的分析结果，但对现在的 debate / self-critique 内容已经开始失配。

## 本地现状

### 1. 分析流程定义已经分叉

- `ai-insight` 仍然把 analyzer 描述为 `Discovery → Evidence → Crucible → Synthesis → Delivery`
- `ai-topic-analyzer` 已改成 `Discovery → Evidence → Deep Search → Smart Synthesis → Delivery`
- `openspec/changes/deep-search-smart-synthesis` 明确要求默认路径切到 Smart Synthesis，且用户文档不再提多轮 debate

这意味着卡片不能再强绑定“固定 2-3 轮辩论”，否则很快会和真实流程脱节。

### 2. 卡片 contract 已经落后于 renderer

- `impact` renderer 实际消费的是字符串数组 `signals: string[]`，但部分测试/文档仍写成对象数组
- `timeline` renderer 实际消费的是 `round/title/summary`，但测试仍写成 `time/event/impact`

这说明“卡片 schema”本身还没稳定，不适合继续堆更多内容到老模板里。

### 3. 真正有用户价值的不是“图表更多”，而是“推演更清楚”

从近期日志看，用户更在意的是：

- 初版判断为什么不成立
- 哪些证据把结论改掉了
- 最终结论是怎么收敛出来的

单纯增加 `radar` 或把 `timeline` 塞满，并不能把这个价值讲清楚。

## 外部调研结论

结合近期 carousel / knowledge-card 的公开经验，可以抽出几个稳定规律：

1. 第一张必须是 hook，不是摘要。
2. 中间页更适合“bite-sized takeaways”，而不是一张图塞完整分析。
3. 用户更愿意保存 checklist、breakdown、before/after、multi-step guide 这类能复用的内容。
4. 轮播最适合“问题 → 证据/转折 → 结论/行动”的故事结构。
5. 同一组卡片要保持视觉一致，减少理解切换成本。
6. 对知识型内容，数据/证据页的作用是建立可信度，不是替代结论页。

## 建议：主卡从“图表卡”转为“结论型故事卡”

### 推荐主形态

默认不再以 `radar` 或 `timeline` 为主，而是改成“结论型故事卡组”：

1. 封面卡
2. 结论卡
3. 证据卡
4. 分歧/修正卡
5. 行动卡

核心原则：

- 一张卡只回答一个问题
- 先给判断，再给证据，再给转折，最后给行动
- 把 debate 产出的价值浓缩成“观点如何被修正”，而不是逐轮复读日志

## 建议卡组

### A. 默认 4 张（最稳）

适合大多数热点分析，也是建议的新默认：

1. `title`
   - 负责点击
   - 只做 hook，不承载分析细节

2. `verdict`
   - 一句话结论
   - 为什么现在值得讲
   - 置信度 / 适用边界

3. `evidence`
   - 3 条最强证据
   - 每条证据说明“支持了什么判断”
   - 带来源名，不必堆满链接

4. `delta`
   - 初版判断哪里被挑战
   - 哪个质疑改变了结论
   - 最终修正后的 stance

### B. 扩展 5-6 张（仅在高信息密度话题启用）

1. `title`
2. `verdict`
3. `evidence`
4. `delta`
5. `action`
6. `appendix`（可选）

其中：

- `action` 适合回答“普通用户 / 开发者 / 企业应该怎么做”
- `appendix` 才轮到 `radar`、source mix、时间线等图表类内容

## 对现有 card 的建议

### `title`

保留，继续做封面。

### `impact`

不要再承担“所有结论信息的总装页”。

建议拆成新的 `verdict`：

- 核心判断
- why now
- confidence
- 1 条 caveat

这样信息密度更适合首张正文卡。

### `radar`

降级为可选附录卡，不要作为默认主卡。

原因：

- 对单话题深挖来说，来源分布不是用户最关心的问题
- 这类图表对“帮助用户转发/收藏”贡献有限
- 它适合给内部判断质量，不适合做对外主叙事

### `timeline`

不建议继续叫 timeline。

如果保留，应该改造成 `delta` 或 `revision`：

- 初版判断
- 主要质疑
- 修正结论

重点不是“第几轮”，而是“哪一次修正改变了判断”。

## 面向未来流程的兼容建议

如果后续彻底切到 Smart Synthesis，没有真实 debate：

- `delta` 依然可以保留
- 但内容应改为：
  - 主要争议点
  - 证据不足点
  - 结论边界

也就是说，主卡应该绑定“推演后的修正/边界”，而不是绑定“Debater 第 N 轮说了什么”。

## 最终建议

### 结论

现在的 card 主形态，应该从：

- `title + impact + radar + timeline`

切到：

- `title + verdict + evidence + delta`

需要补行动建议时，再扩成 5 张：

- `title + verdict + evidence + delta + action`

### 为什么

- 更符合当前用户真正想看的“判断怎么来的”
- 同时兼容 debate 和 Smart Synthesis 两条可能继续摇摆的流程
- 能把复杂推理拆成更适合收藏和转发的知识卡
- 避免继续把核心信息挤进 `impact` 一张卡里
