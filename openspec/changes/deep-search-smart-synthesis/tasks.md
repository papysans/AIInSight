## 1. Remove Crucible Phase

- [x] 1.1 Remove Phase 3 (Crucible) section from SKILL.md
- [x] 1.2 Remove Analyst and Debater persona definitions from SKILL.md
- [x] 1.3 Remove debate_log field from analysis_packet schema in GUIDELINES.md
- [x] 1.4 Remove Section 6 (Debate 终止条件) from GUIDELINES.md

## 2. Implement Deep Search Phase

- [x] 2.1 Add Phase 2.5 (Deep Search) section to SKILL.md after Evidence phase
- [x] 2.2 Define vertical data source list (AIBase, 机器之心, 量子位, TechCrunch, arXiv, GitHub)
- [x] 2.3 Implement site: search query construction for each data source
- [x] 2.4 Add deduplication logic to merge Deep Search results with existing fact_sheet
- [x] 2.5 Add progress display for Deep Search (🔎 emoji format)

## 3. Implement Smart Synthesis Phase

- [x] 3.1 Rename Phase 3 from "Crucible" to "Smart Synthesis" in SKILL.md
- [x] 3.2 Create single-pass Synthesis prompt with embedded critical thinking instructions
- [x] 3.3 Add evidence quality assessment logic (High/Medium/Low credibility scoring)
- [x] 3.4 Implement confidence calculation based on evidence quality (not debate rounds)
- [x] 3.5 Remove multi-round loop logic, replace with single LLM invocation

## 4. Update Mode Configurations

- [x] 4.1 Update quick mode to skip Deep Search (Evidence → Smart Synthesis)
- [x] 4.2 Update standard mode to include 3-5 Deep Search queries
- [x] 4.3 Update deep mode to include full Deep Search (6-9 queries)
- [x] 4.4 Update mode comparison table in SKILL.md

## 5. Testing & Validation

- [ ] 5.1 Test standard mode with Deep Search + Smart Synthesis flow
- [ ] 5.2 Test quick mode skips Deep Search correctly
- [ ] 5.3 Test deep mode executes full vertical source searches
- [ ] 5.4 Verify deduplication works correctly (no duplicate URLs in fact_sheet)
- [ ] 5.5 Verify confidence scores correlate with evidence quality
- [ ] 5.6 Measure latency improvement (target: ~30s faster than old Crucible)

## 6. Documentation Updates

- [x] 6.1 Update SKILL.md header description (remove "Crucible" reference)
- [x] 6.2 Update GUIDELINES.md Section 4 with Deep Search strategy
- [x] 6.3 Add new Section 6 for confidence assessment rules
- [x] 6.4 Update ai-daily-topic-analysis spec to reflect new workflow
