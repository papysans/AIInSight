## Requirement: Crucible phase MUST use independent subagent sessions for Analyst and Debater roles

The ai-topic-analyzer Skill's Phase 3 (Crucible) SHALL execute Analyst and Debater roles in separate subagent sessions via OpenCode's Task tool, rather than simulating both roles within a single context window.

### Scenario: Execute a standard-mode debate round
- **GIVEN** the Skill has completed Phase 2 (Evidence) with a valid fact_sheet
- **WHEN** Phase 3 (Crucible) begins with mode=standard (max_rounds=3)
- **THEN** the Skill MUST invoke Task("analyst") in an independent session, passing fact_sheet as input
- **AND** the Skill MUST invoke Task("debater") in a separate independent session, passing the Analyst's analysis_packet as input
- **AND** each subagent session MUST NOT have access to the other's internal reasoning or context

### Scenario: Analyst receives Debater challenges in subsequent rounds
- **GIVEN** Round 1 Debater returned a list of challenges (not "PASS")
- **WHEN** Round 2 begins
- **THEN** the Skill MUST invoke Task("analyst") with both the original fact_sheet AND the Round 1 challenges
- **AND** the Analyst subagent MUST address each challenge in its revised analysis_packet

### Scenario: Debater approves analysis
- **GIVEN** the Analyst has produced analysis_packet_v2
- **WHEN** Task("debater") is invoked with analysis_packet_v2
- **AND** the Debater returns exactly "PASS"
- **THEN** the Skill MUST terminate the Crucible loop immediately
- **AND** proceed to Phase 4 (Synthesis) with analysis_packet_v2

---

## Requirement: Subagent definitions MUST be self-contained within the Skill

The Skill SHALL NOT require users to manually configure `opencode.json` or manually place agent definition files in `.opencode/agents/`.

### Scenario: First-time Skill execution
- **GIVEN** the user has installed the ai-topic-analyzer Skill files
- **AND** `.opencode/agents/analyst.md` does not exist
- **WHEN** the Skill is invoked for the first time
- **THEN** the Skill MUST either:
  - (Option A) Use Task tool with ad-hoc inline system prompts (if supported by OpenCode)
  - (Option B) Automatically write `analyst.md` and `debater.md` to `.opencode/agents/`
- **AND** the user MUST NOT be required to perform any manual configuration steps

---

## Requirement: Subagent prompts MUST enforce structured output formats

Analyst and Debater subagents SHALL produce outputs in predictable, parseable formats to enable reliable Coordinator logic.

### Scenario: Analyst produces analysis_packet
- **GIVEN** Task("analyst") is invoked
- **WHEN** the Analyst subagent completes
- **THEN** the output MUST be valid JSON conforming to the analysis_packet schema
- **AND** the JSON MUST include: summary, insight, signals[], actions[], confidence

### Scenario: Debater produces challenges
- **GIVEN** Task("debater") is invoked with an analysis_packet
- **WHEN** the Debater finds issues
- **THEN** the output MUST be a numbered list of challenges (e.g., "1. ...\n2. ...")
- **OR** the output MUST be exactly the string "PASS" (no additional text)

---

## Requirement: Crucible termination conditions MUST remain unchanged

The three termination conditions from GUIDELINES.md Section 6 SHALL apply to the subagent-driven implementation.

### Scenario: Debater returns "PASS"
- **WHEN** Task("debater") returns exactly "PASS"
- **THEN** the Crucible loop MUST terminate immediately (Condition 1)

### Scenario: Max rounds reached
- **GIVEN** mode=standard (max_rounds=3)
- **WHEN** Round 3 completes
- **THEN** the Crucible loop MUST terminate regardless of Debater output (Condition 2)

### Scenario: Debater repeats previous challenges
- **GIVEN** Round 2 Debater output is semantically identical to Round 1 output
- **WHEN** the Coordinator detects no new challenges
- **THEN** the Crucible loop MUST terminate (Condition 3: implicit PASS)

---

## Requirement: User-visible display format MUST remain unchanged

The emoji-based progress display SHALL continue to show debate rounds, but content SHALL reflect actual subagent outputs.

### Scenario: Display Round 1 debate
- **GIVEN** Analyst subagent returned analysis with summary="GPT-5 推理突破"
- **AND** Debater subagent returned 2 challenges
- **THEN** the display MUST show:
  ```
  — Round 1 —
  📊 Analyst：GPT-5 推理突破
  🔍 Debater 质疑：
    1. [challenge 1]
    2. [challenge 2]
  ```

### Scenario: Display debate completion
- **GIVEN** Round 2 Debater returned "PASS"
- **THEN** the display MUST show:
  ```
  — Round 2 —
  📊 Analyst（修正版）：[revised summary]
  ✅ Debater：PASS

  ✅ Crucible 完成（2轮），分析已通过辩证检验
  ```

---

## Requirement: Subagents MUST have zero tool access

Analyst and Debater subagents SHALL NOT have access to file system, bash, web search, or any other tools.

### Scenario: Subagent attempts tool use
- **GIVEN** a subagent is configured with tools=[]
- **WHEN** the subagent attempts to call Read, Bash, or WebSearch
- **THEN** the tool call MUST fail or be denied
- **AND** the subagent MUST rely solely on the input provided in the Task prompt

---

## Requirement: Security constraints MUST be embedded in both subagent prompts

Both Analyst and Debater system prompts SHALL include identical content safety constraints.

### Scenario: Analyst detects sensitive topic
- **GIVEN** the fact_sheet contains politically sensitive content
- **WHEN** Task("analyst") processes the input
- **THEN** the Analyst MUST return `{ "blocked": true, "reason": "内容安全策略" }`
- **AND** the Coordinator MUST terminate the entire analysis flow

### Scenario: Debater detects sensitive topic
- **GIVEN** the analysis_packet contains sensitive content
- **WHEN** Task("debater") processes the input
- **THEN** the Debater MUST return `{ "blocked": true, "reason": "内容安全策略" }`
- **AND** the Coordinator MUST terminate the entire analysis flow
