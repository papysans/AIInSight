## MODIFIED Requirements

### Requirement: AI Daily topic analysis MUST preserve structured topic context
When the system analyzes a topic originating from the AI Daily pipeline, it SHALL preserve structured topic context available from the AI Daily topic record, including reusable evidence-related information, instead of reducing the topic to plain text before analysis. The supported remote MCP topology SHALL execute evidence retrieval and reporting in the cloud-side workflow boundary, while multi-round debate SHALL be executed on the host side by default.

#### Scenario: Analyze an AI Daily topic
- **WHEN** a caller requests analysis for a topic that exists in the AI Daily topic store
- **THEN** the analysis path MUST use the structured topic context associated with that topic rather than a title-and-summary-only text surrogate

### Requirement: Supported AI Daily analysis interfaces MUST use equivalent topic fidelity
Supported interfaces for AI Daily topic analysis SHALL use equivalent topic-context fidelity, even if their transport or response model differs. Evidence retrieval and reporter stages SHALL rely on cloud-side workflow orchestration. Multi-round debate (analyst/debater loop) SHALL be executed on the host side by default, with the cloud-side `analyze_topic` full-pipeline path preserved as a backward-compatible fallback.

#### Scenario: HTTP and MCP both analyze the same AI Daily topic
- **WHEN** the same AI Daily topic is analyzed through the dedicated HTTP path and the supported MCP path
- **THEN** both paths MUST rely on equivalent underlying topic context rather than one path using a materially weaker flattened-topic representation

### Requirement: AI Daily analysis guidance MUST describe host-side debate as the default path
User-facing AI Daily guidance SHALL describe the host-side debate workflow (`retrieve_and_report` → host debate → `submit_analysis_result`) as the primary analysis path, and SHALL describe the `analyze_topic` full-pipeline tool as a backward-compatible alternative for clients without host-side LLM capability.

#### Scenario: User selects a daily topic for analysis
- **WHEN** a user chooses a topic from the AI Daily results for deeper analysis
- **THEN** the system guidance MUST present the host-side debate path as the default workflow, while noting the `analyze_topic` full-pipeline fallback for clients that cannot orchestrate host-side debate

### Requirement: Cloud-side workflow MUST expose retrieval+reporter and writer+publish as separate atomic steps
The cloud-side workflow SHALL expose `retrieve_and_report` (source retrieval + reporter) and `submit_analysis_result` (writer + card generation + publish) as independently callable steps, in addition to preserving the existing `analyze_topic` full-pipeline tool.

#### Scenario: Host requests evidence retrieval without triggering debate
- **WHEN** the host calls `retrieve_and_report` for a topic
- **THEN** the cloud MUST execute only source retrieval and reporter stages, returning `evidence_bundle`, `news_content`, and `source_stats` without proceeding to debate, writer, or publish stages
