## ADDED Requirements

### Requirement: Deep Search MUST execute targeted searches across vertical data sources

The system SHALL execute targeted searches across vertical AI data sources (AIBase, 机器之心, TechCrunch, arXiv, GitHub Trending) after Evidence phase and before Synthesis phase.

#### Scenario: Execute deep search for a hot topic
- **WHEN** Phase 2 (Evidence) completes with a valid fact_sheet
- **AND** mode is standard or deep (not quick)
- **THEN** the system MUST execute 3-5 targeted site: searches across vertical data sources
- **AND** each search MUST use the topic title as the query term
- **AND** results MUST be appended to the existing fact_sheet

#### Scenario: Skip deep search in quick mode
- **WHEN** mode is quick
- **THEN** the system MUST skip Deep Search phase entirely
- **AND** proceed directly from Evidence to Smart Synthesis

### Requirement: Deep Search MUST target specific vertical data sources

The system SHALL use site-specific search queries to target vertical AI data sources.

#### Scenario: Search Chinese AI media sources
- **WHEN** Deep Search executes for a topic
- **THEN** the system MUST include searches for:
  - `"{topic}" site:aibase.com`
  - `"{topic}" site:jiqizhixin.com`
  - `"{topic}" site:qbitai.com`

#### Scenario: Search English technical sources
- **WHEN** Deep Search executes in deep mode
- **THEN** the system MUST include searches for:
  - `"{topic}" site:techcrunch.com`
  - `"{topic}" site:arxiv.org abstract`
  - `"{topic}" site:github.com trending`

### Requirement: Deep Search results MUST be deduplicated with existing evidence

The system SHALL deduplicate Deep Search results against existing Evidence phase results before appending to fact_sheet.

#### Scenario: Deduplicate by URL
- **WHEN** Deep Search returns a result with URL already in fact_sheet
- **THEN** the system MUST skip that result
- **AND** NOT append it to fact_sheet

#### Scenario: Merge duplicate events from different sources
- **WHEN** Deep Search returns a result describing the same event as an existing fact_sheet entry
- **THEN** the system MUST merge the URLs into the existing entry
- **AND** NOT create a duplicate fact_sheet entry
