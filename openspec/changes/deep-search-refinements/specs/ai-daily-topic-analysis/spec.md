## MODIFIED Requirements

### Requirement: AI Daily analysis guidance MUST describe host-side Smart Synthesis as the default path
User-facing AI Daily guidance SHALL describe the host-side Smart Synthesis workflow (`retrieve_and_report` → Deep Search → Smart Synthesis → `submit_analysis_result`) as the primary analysis path. The Smart Synthesis prompt SHALL include an evidence-insufficiency degradation instruction that explicitly marks conclusions as preliminary when High credibility evidence is scarce.

#### Scenario: Smart Synthesis with insufficient evidence triggers degradation label
- **WHEN** Smart Synthesis receives a fact_sheet with fewer than 3 High credibility sources
- **THEN** the analysis output MUST prefix conclusions with "证据有限，以下为初步判断"
- **AND** confidence score MUST be below 0.5

### Requirement: Confidence assessment MUST use fine-grained tiers instead of broad ranges
The system SHALL assess confidence using 4 tiers instead of 3, splitting the previous 0.5-0.79 range into two sub-tiers based on both credibility count and dimension coverage.

#### Scenario: High confidence with strong multi-dimensional evidence
- **WHEN** fact_sheet contains ≥5 High credibility sources
- **AND** evidence covers 3 dimensions (Technical/Market/Sentiment)
- **THEN** confidence MUST be 0.8-1.0

#### Scenario: Medium-high confidence with good evidence and partial coverage
- **WHEN** fact_sheet contains 3-4 High credibility sources
- **AND** evidence covers 2 dimensions
- **THEN** confidence MUST be 0.65-0.79

#### Scenario: Medium-low confidence with limited evidence or single dimension
- **WHEN** fact_sheet contains 3-4 High credibility sources
- **AND** evidence covers only 1 dimension
- **THEN** confidence MUST be 0.5-0.64

#### Scenario: Low confidence with weak evidence
- **WHEN** fact_sheet contains fewer than 3 High credibility sources
- **OR** evidence is primarily Low/Medium credibility
- **THEN** confidence MUST be below 0.5

### Requirement: Deep Search arXiv queries MUST include temporal filtering
The Deep Search phase SHALL append `{current_year}` to arXiv site-search queries to avoid returning outdated papers.

#### Scenario: arXiv search in standard or deep mode
- **WHEN** Deep Search executes an arXiv site-search query
- **THEN** the query MUST include `{current_year}` as a temporal filter
- **AND** the query format MUST be `"{topic}" site:arxiv.org abstract {current_year}`

### Requirement: Deep mode MUST degrade gracefully on rate limit errors
The system SHALL detect consecutive search failures during Deep Search and automatically reduce the remaining search count to standard-mode levels.

#### Scenario: Consecutive search failures in deep mode
- **WHEN** Deep Search encounters 2 or more consecutive search errors (timeout, rate limit, or empty results)
- **THEN** the system MUST reduce remaining Deep Search queries to a maximum of 3 (standard mode level)
- **AND** the system MUST display a degradation notice to the user: "🔎 搜索受限，已降级为 standard 模式搜索量"
- **AND** the system MUST NOT retry the failed queries
