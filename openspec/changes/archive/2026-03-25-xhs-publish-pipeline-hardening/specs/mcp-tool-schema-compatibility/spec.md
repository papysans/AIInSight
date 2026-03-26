## MODIFIED Requirements

### Requirement: Public MCP tool schemas MUST be downstream-compatible
Every tool exposed in the public MCP tool list SHALL publish an input schema that is valid for downstream MCP/OpenAI-compatible consumers and MUST avoid schema shapes that fail tool discovery or registration. All XHS-related tools SHALL include an optional `account_id` string property in their input schema to enable explicit multi-account targeting.

#### Scenario: Client loads public MCP tool definitions
- **WHEN** a downstream client requests the public MCP tool list
- **THEN** each exposed tool schema MUST be accepted by the supported tool-consumer stack without schema-validation failure during discovery

#### Scenario: XHS tool is called with account_id
- **WHEN** an AI caller invokes any XHS tool (`publish_xhs_note`, `check_xhs_status`, `get_xhs_login_qrcode`, `check_xhs_login_session`, `submit_xhs_verification`) with an `account_id` argument
- **THEN** the tool handler MUST pass that `account_id` through the entire execution chain to the xhs-mcp sidecar

#### Scenario: XHS tool is called without account_id
- **WHEN** an AI caller invokes any XHS tool without providing `account_id`
- **THEN** the tool handler MUST fall back to `get_account_id()` context or `"_default"`, preserving backward compatibility
