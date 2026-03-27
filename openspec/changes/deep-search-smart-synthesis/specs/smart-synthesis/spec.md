## ADDED Requirements

### Requirement: Smart Synthesis MUST generate analysis in a single pass with embedded critical thinking

The system SHALL generate analysis_packet in a single LLM invocation with critical thinking embedded in the prompt, rather than using multi-round debate.

#### Scenario: Generate analysis with critical thinking
- **WHEN** Smart Synthesis receives fact_sheet from Deep Search phase
- **THEN** the system MUST invoke a single LLM call with a prompt that includes:
  - Instructions to consider counter-evidence
  - Instructions to self-assess confidence based on evidence quality
  - Instructions to identify gaps or uncertainties
- **AND** output a complete analysis_packet conforming to the schema

#### Scenario: Quick mode bypasses Deep Search but uses Smart Synthesis
- **WHEN** mode is quick
- **THEN** the system MUST skip Deep Search
- **AND** proceed directly to Smart Synthesis with Evidence phase output
- **AND** Smart Synthesis MUST still apply critical thinking in a single pass

### Requirement: Smart Synthesis MUST assess confidence based on evidence quality

The system SHALL calculate confidence score based on evidence credibility and coverage, not debate rounds.

#### Scenario: High confidence with strong evidence
- **WHEN** fact_sheet contains ≥5 High credibility sources
- **AND** evidence covers multiple dimensions (Technical/Market/Sentiment)
- **THEN** confidence score MUST be ≥0.8

#### Scenario: Medium confidence with mixed evidence
- **WHEN** fact_sheet contains 3-4 High credibility sources
- **OR** evidence covers only 1-2 dimensions
- **THEN** confidence score MUST be 0.5-0.79

#### Scenario: Low confidence with weak evidence
- **WHEN** fact_sheet contains <3 High credibility sources
- **OR** evidence is primarily Low/Medium credibility
- **THEN** confidence score MUST be <0.5
