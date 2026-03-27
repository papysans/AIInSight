## MODIFIED Requirements

### Requirement: AI Daily analysis guidance MUST describe host-side Smart Synthesis as the default path

User-facing AI Daily guidance SHALL describe the host-side Smart Synthesis workflow (`retrieve_and_report` → Deep Search → Smart Synthesis → `submit_analysis_result`) as the primary analysis path, replacing the previous multi-round debate approach.

#### Scenario: User selects a daily topic for analysis
- **WHEN** a user chooses a topic from the AI Daily results for deeper analysis
- **THEN** the system guidance MUST present the Deep Search + Smart Synthesis path as the default workflow
- **AND** the system MUST NOT reference multi-round debate in user-facing documentation

### Requirement: Host-side analysis MUST use Deep Search + Smart Synthesis instead of multi-round debate

The host-side analysis workflow SHALL execute Deep Search followed by Smart Synthesis, rather than the previous Crucible multi-round debate loop.

#### Scenario: Standard mode analysis with Deep Search
- **WHEN** the host executes analysis in standard mode
- **THEN** the workflow MUST be: Discovery → Evidence → Deep Search → Smart Synthesis → Delivery
- **AND** the system MUST NOT execute Analyst ↔ Debater debate rounds

#### Scenario: Quick mode skips Deep Search
- **WHEN** the host executes analysis in quick mode
- **THEN** the workflow MUST be: Discovery → Evidence → Smart Synthesis → Delivery
- **AND** Deep Search phase MUST be skipped
