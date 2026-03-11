## MODIFIED Requirements

### Requirement: Docker-first XHS verification SHALL cover sidecar availability and login state
The system SHALL verify that the Docker-based `xhs-mcp` sidecar is reachable and authenticated before XHS publishing is considered ready, and SHALL distinguish a merely logged-in state from a publish-ready state when publish workflows require stronger validation.

#### Scenario: Operator validates Docker XHS readiness
- **WHEN** the operator triggers XHS readiness validation
- **THEN** the system MUST report whether the sidecar is reachable, whether login is complete, and whether the runtime appears publish-ready or still requires operator recovery

### Requirement: Supported public XHS guidance SHALL exclude host-side runtime as a primary path
Public-facing docs and operator guidance for the migrated XHS flow SHALL describe Docker-first deployment as the supported path and SHALL provide enough runtime/version context to diagnose stale-container suspicions without restoring host-side `xhs-mcp` as a parallel supported chain.

#### Scenario: User investigates Docker runtime skew during XHS publish debugging
- **WHEN** a user or operator checks the running XHS integration during publish troubleshooting
- **THEN** the system guidance and diagnostics MUST make it possible to tell whether API and MCP containers are aligned with the intended Docker-first publish flow
