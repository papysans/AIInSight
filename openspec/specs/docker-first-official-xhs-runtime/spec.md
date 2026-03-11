## ADDED Requirements

### Requirement: Docker sidecar SHALL be the supported XHS runtime topology
The system SHALL define a Docker-based `xhs-mcp` sidecar runtime as the supported Xiaohongshu integration topology for this migration and SHALL route AIInSight XHS traffic to that sidecar over the Docker network.

#### Scenario: XHS integration is configured for supported deployment
- **WHEN** the supported XHS deployment is brought up
- **THEN** AIInSight services MUST connect to an `xhs-mcp` sidecar endpoint within the Docker topology rather than requiring a host-side MCP process

### Requirement: Docker-first XHS verification SHALL cover sidecar availability and login state
The system SHALL verify that the Docker-based `xhs-mcp` sidecar is reachable and authenticated before XHS publishing is considered ready.

#### Scenario: Operator validates Docker XHS readiness
- **WHEN** the operator triggers XHS readiness validation
- **THEN** the system MUST report whether the sidecar is reachable, whether login is complete, and whether operator scanning is still required

### Requirement: Supported public XHS guidance SHALL exclude host-side runtime as a primary path
Public-facing docs and operator guidance for the migrated XHS flow SHALL describe Docker-first deployment as the supported path and SHALL NOT present host-side `xhs-mcp` as a parallel supported chain.

#### Scenario: User reads XHS deployment guidance
- **WHEN** a public-facing XHS setup or troubleshooting guide describes the supported deployment path
- **THEN** it MUST present the Docker sidecar topology as the primary supported chain and MUST NOT describe host-side `xhs-mcp` as a supported alternative for this migration
