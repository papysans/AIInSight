## AI 代码搜索工具协作策略

**CRITICAL：回答任何代码相关问题前，必须先调用搜索工具定位代码。禁止猜测或凭经验假设代码位置。**

### 工具优先级

1. **已知函数名/类名** → `Grep`
2. **理解业务逻辑 / 探索代码 / 查找实现** → `Augment codebase-retrieval`（返回完整代码片段，语义理解最强）
3. **Augment 结果不足** → `Fast-Context fast_context_search`（返回文件路径+行号，附带 grep 关键词建议）
4. **Fast-Context 返回 grep keywords** → 立即用 `Grep` 二次精确搜索
5. **需要理解模块架构 / 子项目结构** → `ContextWeaver codebase-retrieval`（擅长返回架构文档和目录树）
6. **仍未找到** → 组合 Glob + Read + Grep

### 三引擎特性与选型

| 场景 | 首选工具 | 原因 |
|------|---------|------|
| 快速定位文件位置 | Fast-Context | 轻量 ~2KB，带 grep keywords 可二次精搜 |
| 读懂代码逻辑 / 一步到位 | Augment | 返回完整代码片段，语义精度最高 |
| 理解模块架构 / 目录结构 | ContextWeaver | 擅长拉取架构文档、Mermaid 图、目录树 |
| 跨文件追踪调用链 | Augment → Fast-Context | 先语义定位，再路径扩展 |

### 推荐参数

**Fast-Context：** `max_results: 8, max_turns: 2, tree_depth: 2`。结果不足时提高 `max_turns` 到 3、`tree_depth` 到 3。

**ContextWeaver：** 使用 `technical_terms` 传入已知的类名/函数名可提高精度。探索性查询留空即可。

### 禁止行为

- 猜测代码位置（"应该在 service/firmware 里"）
- 跳过搜索直接回答（"根据框架惯例，应该是..."）
- 遇到搜索就启动 Task/Explore 子代理（Augment + Fast-Context + ContextWeaver + Grep 组合优先）

### 子代理使用条件

仅当需要读取 10+ 文件交叉比对、或多轮搜索会撑爆上下文时，才启动子代理。
