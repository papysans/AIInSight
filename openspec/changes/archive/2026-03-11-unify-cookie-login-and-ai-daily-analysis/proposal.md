## Why

AIInSight's current user-facing XHS login story is inconsistent: the real operational path is browser-side cookie extraction plus cookie injection, but the repository still contains QR-login artifacts, mixed documentation, and partially exposed helper paths that blur the public contract. At the same time, the `upload_xhs_cookies` MCP tool currently advertises an invalid or OpenAI-incompatible schema shape, and `analyze_ai_topic` follows a weaker MCP path than the dedicated AI Daily HTTP analysis flow.

## What Changes

- Remove QR-code login guidance and legacy-facing materials from the supported XHS login flow, and standardize documentation and public behavior around cookie injection only.
- Tighten MCP tool schemas so exposed tools are valid for downstream MCP/OpenAI consumers, especially `upload_xhs_cookies`.
- Clarify the public MCP surface so only supported login-related tools and payloads are documented and exposed.
- Improve `analyze_ai_topic` so AI Daily topic analysis preserves more topic context and aligns better with the higher-fidelity AI Daily analysis path.
- Update supporting docs, skill guidance, and integration contracts so the system communicates one authoritative login path and one clear analysis behavior.

## Capabilities

### New Capabilities
- `cookie-based-xhs-auth`: Defines cookie injection as the only supported XHS login path for agent and MCP workflows.
- `mcp-tool-schema-compatibility`: Defines compatibility and validation requirements for public MCP tool schemas exposed to downstream clients.
- `ai-daily-topic-analysis`: Defines consistent, high-fidelity analysis behavior for AI Daily topics across supported interfaces.

### Modified Capabilities

None.

## Impact

- Affected code: `opinion_mcp/server.py`, `opinion_mcp/tools/ai_daily.py`, `opinion_mcp/tools/publish.py`, `opinion_mcp/services/backend_client.py`, `app/api/endpoints.py`, `app/services/ai_daily_workflow_adapter.py`, `app/services/workflow.py`, and related XHS publishing/auth services.
- Affected docs and skills: AI Insight skill guidance, XHS architecture docs, usage guides, and login-related operational documentation.
- Affected systems: MCP tool discovery/registration, OpenCode/OpenAI-compatible tool consumers, AI Daily topic analysis orchestration, and XHS login/publish operator flow.
