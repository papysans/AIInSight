# Tasks: Subagent-Driven Debate Implementation

## Phase 1: Investigation & Validation

### Task 1.1: Verify OpenCode Task tool capabilities
**Owner**: Unassigned
**Status**: TODO
**Description**: 确认 OpenCode 的 Task tool 是否支持 ad-hoc inline prompt（不预注册 agent，直接传 system prompt）。

**Acceptance Criteria**:
- 阅读 OpenCode 官方文档或源码，确认 Task tool 的参数支持
- 测试是否可以不在 `opencode.json` 中预注册 agent，直接通过 Task 调用传入完整 system prompt
- 记录结果：支持 → 采用 Option A；不支持 → 采用 Option B

---

### Task 1.2: Design subagent prompt templates
**Owner**: Unassigned
**Status**: TODO
**Description**: 设计 Analyst 和 Debater 的 system prompt 模板，确保输出格式可解析。

**Acceptance Criteria**:
- Analyst prompt 强制 JSON schema 输出
- Debater prompt 强制 "PASS" 或编号列表格式
- 两个 prompt 都内嵌安全约束
- Prompt 模板支持动态插入 fact_sheet / challenges

---

## Phase 2: Core Implementation

### Task 2.1: Implement Coordinator loop logic
**Owner**: Unassigned
**Status**: TODO
**Description**: 在 SKILL.md Phase 3 中实现 Crucible 的 Coordinator 循环逻辑。

**Acceptance Criteria**:
- 实现 `for round in 1..max_rounds` 循环
- 每轮调用 Task("analyst") 和 Task("debater")
- 实现三个终止条件的判断逻辑
- 构建 debate_log 记录完整对话历史

**Files**:
- `.agents/skills/ai-topic-analyzer/SKILL.md` (Phase 3 section)

---

### Task 2.2: Implement subagent invocation
**Owner**: Unassigned
**Status**: TODO
**Description**: 根据 Task 1.1 的结果，实现 subagent 调用方式（Option A 或 Option B）。

**Acceptance Criteria**:
- Option A: 构造 Task 调用时传入完整 inline prompt
- Option B: Skill 启动时检查并自动写入 `.opencode/agents/analyst.md` + `debater.md`
- 确保 subagent 配置 tools=[]（零工具权限）

**Files**:
- `.agents/skills/ai-topic-analyzer/SKILL.md` (Phase 3 section)
- `.opencode/agents/analyst.md` (if Option B)
- `.opencode/agents/debater.md` (if Option B)

---

### Task 2.3: Implement output parsing logic
**Owner**: Unassigned
**Status**: TODO
**Description**: 实现 Coordinator 解析 subagent 输出的逻辑。

**Acceptance Criteria**:
- 解析 Analyst 返回的 JSON，提取 analysis_packet
- 解析 Debater 返回的文本，识别 "PASS" 或提取 challenges 列表
- 处理解析失败的情况（格式错误、JSON 不合法等）
- 实现重复 challenge 检测逻辑（Condition 3）

**Files**:
- `.agents/skills/ai-topic-analyzer/SKILL.md` (Phase 3 section)

---

## Phase 3: Display & Integration

### Task 3.1: Preserve emoji display format
**Owner**: Unassigned
**Status**: TODO
**Description**: 确保用户可见的 debate 展示格式与现有格式一致。

**Acceptance Criteria**:
- 保持 `🧪 Crucible 启动` 开头
- 保持 `— Round N —` 分隔符
- 保持 `📊 Analyst` / `🔍 Debater` / `✅ Debater: PASS` emoji 标记
- 内容来自真实 subagent 输出，而非模拟

**Files**:
- `.agents/skills/ai-topic-analyzer/SKILL.md` (Phase 3 section)

---

### Task 3.2: Update GUIDELINES.md
**Owner**: Unassigned
**Status**: TODO
**Description**: 更新 GUIDELINES.md Section 6 (Debate 终止条件)，说明 subagent 模式的执行方式。

**Acceptance Criteria**:
- 说明 Analyst 和 Debater 在独立 session 中执行
- 保持三个终止条件不变
- 补充 subagent 输出格式要求

**Files**:
- `.agents/skills/shared/GUIDELINES.md` (Section 6)

---

## Phase 4: Testing & Validation

### Task 4.1: Test standard mode (3 rounds)
**Owner**: Unassigned
**Status**: TODO
**Description**: 测试 standard 模式的完整 Crucible 流程。

**Test Cases**:
- Round 1 Debater 提出质疑 → Round 2 Analyst 修正 → Round 2 Debater PASS
- Round 1-3 Debater 持续质疑 → 达到 max_rounds 强制终止
- Round 2 Debater 重复 Round 1 质疑 → 触发 Condition 3 终止

---

### Task 4.2: Test quick mode (skip Crucible)
**Owner**: Unassigned
**Status**: TODO
**Description**: 确认 quick 模式跳过 Phase 3，直接从 Evidence 进入 Synthesis。

**Test Cases**:
- quick 模式不调用任何 subagent
- 输出中不包含 Crucible 相关展示

---

### Task 4.3: Test deep mode (5 rounds)
**Owner**: Unassigned
**Status**: TODO
**Description**: 测试 deep 模式的 5 轮 debate。

**Test Cases**:
- 验证最多执行 5 轮
- 验证延迟和 token 开销在可接受范围内

---

### Task 4.4: Test security constraints
**Owner**: Unassigned
**Status**: TODO
**Description**: 测试安全约束在 subagent 中的生效情况。

**Test Cases**:
- 输入敏感话题 → Analyst 返回 `blocked: true`
- Analyst 输出敏感内容 → Debater 返回 `blocked: true`
- Coordinator 正确终止流程并向用户展示阻断信息

---

## Phase 5: Documentation

### Task 5.1: Update Skill README
**Owner**: Unassigned
**Status**: TODO
**Description**: 更新 Skill 的 README，说明 subagent 模式的工作原理。

**Acceptance Criteria**:
- 说明 Crucible 使用独立 subagent 执行
- 说明安装方式（零配置 or 自动安装 agent 文件）
- 说明性能影响（延迟 +100%, token +100%）

---

### Task 5.2: Add troubleshooting guide
**Owner**: Unassigned
**Status**: TODO
**Description**: 添加常见问题排查指南。

**Acceptance Criteria**:
- 如何检查 subagent 是否正确安装
- 如何调试 Task 调用失败
- 如何查看 subagent 的原始输出（用于排查格式问题）
