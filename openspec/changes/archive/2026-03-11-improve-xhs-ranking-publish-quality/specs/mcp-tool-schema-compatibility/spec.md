## MODIFIED Requirements

### Requirement: Public MCP tool schemas MUST be downstream-compatible
Every tool exposed in the public MCP tool list SHALL publish an input schema that is valid for downstream MCP/OpenAI-compatible consumers and MUST avoid schema shapes that fail tool discovery or registration.

#### Scenario: Client loads public MCP tool definitions
- **WHEN** a downstream client requests the public MCP tool list
- **THEN** each exposed tool schema MUST be accepted by the supported tool-consumer stack without schema-validation failure during discovery

### Requirement: Public MCP contract MUST match public guidance
Only tools that are actually exposed in the public MCP tool list SHALL be described as callable public MCP tools in skills and public-facing documentation.

#### Scenario: Skills or docs reference an MCP tool
- **WHEN** a skill or public-facing document names an MCP tool as part of the supported workflow
- **THEN** that tool MUST exist in the public MCP tool list, preserve important publish-result metadata from backend responses, and use the same public argument contract described in the guidance
