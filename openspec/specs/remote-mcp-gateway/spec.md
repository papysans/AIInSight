## ADDED Requirements

### Requirement: AIInSight SHALL expose a single remote MCP gateway as the public operator entrypoint
The system SHALL provide one public remote MCP endpoint that aggregates the supported AI analysis, card generation, XHS login, and XHS publishing tools for end users.

#### Scenario: User configures AIInSight in a client
- **WHEN** a user sets up AIInSight in an MCP-capable client
- **THEN** the user MUST only need one remote MCP endpoint rather than separate endpoints for analysis, rendering, or XHS runtime services

### Requirement: Public remote MCP tools SHALL preserve the existing public tool contract
The public remote MCP gateway SHALL continue to expose the existing supported tool names and compatible argument contracts required by AIInSight skills and client workflows.

#### Scenario: Existing skill references public tool names
- **WHEN** a skill or client workflow invokes `analyze_topic`, `publish_to_xhs`, `check_xhs_status`, or `get_xhs_login_qrcode`
- **THEN** the remote MCP gateway MUST expose those tools with compatible public argument contracts

### Requirement: Remote MCP guidance SHALL treat local multi-service runtime as a development-only topology
Public guidance for the remote MCP gateway SHALL treat local `docker compose` as a development or self-hosted topology rather than as the primary end-user setup path.

#### Scenario: User reads setup guidance for AIInSight skill usage
- **WHEN** a public-facing setup guide explains how to use AIInSight skills
- **THEN** it MUST describe the single remote MCP gateway as the primary path and MUST NOT require end users to understand or start local `api` / `mcp` / `renderer` / `xhs-mcp` services

### Requirement: Remote MCP gateway SHALL expose `retrieve_and_report` as a public tool
The gateway SHALL expose a `retrieve_and_report` tool that executes only the source retrieval and reporter stages of the analysis workflow, returning evidence bundle, news content, and source statistics to the caller without proceeding to debate or downstream stages.

#### Scenario: Host skill requests evidence for host-side debate
- **WHEN** a host skill or client calls `retrieve_and_report` with a topic and source configuration
- **THEN** the gateway MUST return `evidence_bundle`, `news_content`, and `source_stats` from cloud-side retrieval and reporter execution, without triggering analyst, debater, writer, or publish stages

### Requirement: Remote MCP gateway SHALL expose `submit_analysis_result` as a public tool
The gateway SHALL expose a `submit_analysis_result` tool that accepts host-side debate output (final analysis, debate history, and context) and continues the cloud-side workflow from the writer stage through card generation and optional publish.

#### Scenario: Host skill submits debate results for writing and publishing
- **WHEN** a host skill or client calls `submit_analysis_result` with final analysis text, debate history, topic context, and source statistics
- **THEN** the gateway MUST execute the writer, card generation, and optional publish stages using the submitted analysis, and MUST return the generated copy, card URLs, and any publish results
