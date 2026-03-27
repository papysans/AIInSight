## ADDED Requirements

### Requirement: Internal cloud services SHALL preserve separated execution boundaries
The cloud-hosted AIInSight deployment SHALL preserve separated internal service boundaries for MCP gateway, backend API/workflow execution, renderer, and XHS runtime.

#### Scenario: Cloud deployment is provisioned
- **WHEN** the supported cloud deployment is brought up
- **THEN** analysis orchestration, rendering, and XHS runtime execution MUST run behind internal service boundaries rather than as one public monolith

### Requirement: Only the MCP gateway SHALL be publicly exposed by default
The supported cloud topology SHALL expose the MCP gateway publicly and SHALL keep backend API, renderer, and XHS runtime services on private/internal network paths by default.

#### Scenario: Operator deploys the supported cloud topology
- **WHEN** the system is deployed in its supported remote form
- **THEN** only the MCP gateway MUST require public ingress and the other services MUST remain internal by default

### Requirement: Cloud topology SHALL support persistent XHS runtime state per account
The cloud deployment SHALL provide persistent storage for XHS runtime account/session state scoped to each account, so that each user's XHS login state is isolated and can survive service restarts independently. This SHALL leverage ShunL xhs-mcp's native SQLite per-account session persistence (as established in `shunl-xhs-mcp-integration` change), with the SQLite database file backed by a persistent Docker volume.

#### Scenario: XHS runtime restarts in cloud deployment
- **WHEN** the XHS runtime service restarts
- **THEN** each account's persisted session state in the ShunL SQLite database MUST remain available after restart via the mounted volume, and one account's restart/re-login MUST NOT affect another account's session

### Requirement: MCP Gateway SHALL authenticate requests and extract account identity
The MCP Gateway SHALL require API key authentication on all public tool calls and SHALL extract an `account_id` from valid credentials to propagate to all internal services.

#### Scenario: Unauthenticated request reaches Gateway
- **WHEN** a request arrives at the public MCP gateway without a valid API key
- **THEN** the gateway MUST reject the request before forwarding to any internal service

#### Scenario: Authenticated request reaches internal services
- **WHEN** a request with a valid API key is accepted by the Gateway
- **THEN** all internal service calls triggered by that request MUST carry the resolved `account_id`

### Requirement: Internal services SHALL isolate state by account
All stateful internal services (job management, workflow status, user settings, XHS sessions, output artifacts) SHALL partition their state by `account_id` so that one account's data is not visible to or modifiable by another account.

#### Scenario: User A queries analysis status
- **WHEN** user A calls `get_analysis_status` or `get_analysis_result` without a specific job_id
- **THEN** the system MUST return only jobs owned by user A, not jobs from any other account

#### Scenario: User A accesses output artifacts
- **WHEN** user A requests card previews, markdown outputs, or login QR codes via API
- **THEN** the system MUST only serve artifacts belonging to user A's account

### Requirement: Job concurrency SHALL be controlled per account, not globally
The job management system SHALL allow multiple accounts to run analysis tasks concurrently, with concurrency limits applied per account rather than as a single global lock.

#### Scenario: User A and User B both start analysis
- **WHEN** user A has a running analysis task and user B submits a new analysis request
- **THEN** user B's request MUST NOT be rejected due to user A's running task
