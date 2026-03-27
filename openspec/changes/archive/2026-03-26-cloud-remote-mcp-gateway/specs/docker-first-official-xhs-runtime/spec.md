## MODIFIED Requirements

### Requirement: Docker sidecar SHALL be the supported XHS runtime topology
The system SHALL define a Docker-based `xhs-mcp` sidecar runtime (ShunL12324/xhs-mcp, as specified in `shunl-xhs-mcp-integration` change) as the supported Xiaohongshu integration topology and SHALL route AIInSight XHS traffic to that sidecar over the supported deployment network, whether local development or cloud-internal runtime.

#### Scenario: XHS integration is configured for supported deployment
- **WHEN** the supported XHS deployment is brought up
- **THEN** AIInSight services MUST connect to a ShunL xhs-mcp sidecar endpoint (`@sillyl12324/xhs-mcp`) within the supported deployment topology rather than requiring a host-side MCP process

### Requirement: Docker-first XHS verification SHALL cover sidecar availability and login state
The system SHALL verify that the Docker-based `xhs-mcp` sidecar is reachable and authenticated before XHS publishing is considered ready, and SHALL support that verification in both local development and cloud-internal sidecar topologies.

#### Scenario: Operator validates Docker XHS readiness
- **WHEN** the operator triggers XHS readiness validation
- **THEN** the system MUST report whether the sidecar is reachable, whether login is complete, and whether operator scanning is still required

### Requirement: XHS sidecar SHALL support multi-account operation in cloud topology
The cloud-internal XHS sidecar SHALL leverage ShunL xhs-mcp's native multi-account capabilities (`xhs_add_account` with `account` parameter, SQLite per-account session persistence, multi-account pool management) to support multiple skill users, each with their own independent XHS login state.

#### Scenario: Two users log into separate XHS accounts
- **WHEN** user A and user B each complete the XHS QR login flow via the same sidecar
- **THEN** each user's session MUST be stored independently in the sidecar's SQLite database, and one user's login/logout MUST NOT affect the other user's session

#### Scenario: User publishes content using their own XHS account
- **WHEN** a user calls `publish_to_xhs` through the Gateway
- **THEN** the system MUST route the publish request to that user's specific XHS account in the sidecar (via the `account` parameter) rather than a shared/global account

### Requirement: Supported public XHS guidance SHALL exclude host-side runtime as a primary path
Public-facing XHS setup and troubleshooting guidance SHALL describe the supported XHS runtime as either cloud-internal sidecar or development Docker topology and SHALL NOT present host-side `xhs-mcp` as the primary supported end-user chain.

#### Scenario: User reads XHS deployment guidance
- **WHEN** a public-facing XHS setup or troubleshooting guide describes the supported deployment path
- **THEN** it MUST present the remote/cloud-internal sidecar topology as the primary supported chain and MUST NOT describe host-side `xhs-mcp` as the primary end-user setup path
