## ADDED Requirements

### Requirement: AI Daily topic analysis MUST preserve structured topic context
When the system analyzes a topic originating from the AI Daily pipeline, it SHALL preserve structured topic context available from the AI Daily topic record, including reusable evidence-related information, instead of reducing the topic to plain text before analysis.

#### Scenario: Analyze an AI Daily topic
- **WHEN** a caller requests analysis for a topic that exists in the AI Daily topic store
- **THEN** the analysis path MUST use the structured topic context associated with that topic rather than a title-and-summary-only text surrogate

### Requirement: Supported AI Daily analysis interfaces MUST use equivalent topic fidelity
Supported interfaces for AI Daily topic analysis SHALL use equivalent topic-context fidelity, even if their transport or response model differs.

#### Scenario: HTTP and MCP both analyze the same AI Daily topic
- **WHEN** the same AI Daily topic is analyzed through the dedicated HTTP path and the supported MCP path
- **THEN** both paths MUST rely on equivalent underlying topic context rather than one path using a materially weaker flattened-topic representation

### Requirement: AI Daily analysis guidance MUST remain aligned with topic-first operator flow
User-facing AI Daily guidance SHALL keep the operator flow centered on selecting a topic from the daily report and analyzing that topic with the system's supported depth options.

#### Scenario: User selects a daily topic for analysis
- **WHEN** a user chooses a topic from the AI Daily results for deeper analysis
- **THEN** the system guidance MUST continue to treat that request as AI Daily topic analysis rather than as a generic free-text topic analysis flow
