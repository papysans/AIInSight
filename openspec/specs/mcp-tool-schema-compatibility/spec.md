## MODIFIED Requirements

### Requirement: Public MCP tool schemas MUST be downstream-compatible
Every tool exposed in the public MCP tool list SHALL publish an input schema that is valid for downstream MCP/OpenAI-compatible consumers and MUST avoid schema shapes that fail tool discovery or registration. This requirement SHALL apply to the single remote MCP gateway contract exposed to end users, including the newly added `retrieve_and_report` and `submit_analysis_result` tools.

#### Scenario: Client loads public MCP tool definitions
- **WHEN** a downstream client requests the public MCP tool list
- **THEN** each exposed tool schema (including `retrieve_and_report` and `submit_analysis_result`) MUST be accepted by the supported tool-consumer stack without schema-validation failure during discovery

### Requirement: Public MCP contract MUST match public guidance
Only tools that are actually exposed in the public MCP tool list SHALL be described as callable public MCP tools in skills and public-facing documentation. Public guidance for the remote MCP gateway SHALL describe one public tool surface rather than multiple user-visible backend service surfaces.

#### Scenario: Skills or docs reference an MCP tool
- **WHEN** a skill or public-facing document names an MCP tool as part of the supported workflow
- **THEN** that tool MUST exist in the public MCP tool list and use the same public argument contract described in the guidance

### Requirement: New host-debate tools MUST be included in the public tool contract
The `retrieve_and_report` and `submit_analysis_result` tools SHALL be registered in the public MCP tool list alongside existing tools, and their schemas MUST follow the same compatibility requirements as all other public tools.

#### Scenario: Skill references host-debate tools
- **WHEN** the ai-topic-analyzer skill describes the host-side debate workflow using `retrieve_and_report` and `submit_analysis_result`
- **THEN** both tools MUST be present in the public MCP tool list with schemas that match the skill's documented argument contracts
