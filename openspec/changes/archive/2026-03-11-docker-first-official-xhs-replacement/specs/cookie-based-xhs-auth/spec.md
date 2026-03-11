## MODIFIED Requirements

### Requirement: Official upstream login flow is the supported public XHS authentication path
The system SHALL define the upstream official Xiaohongshu authentication workflow exposed by `xiaohongshu-mcp` as the supported public authentication flow for Xiaohongshu operations exposed through skills, MCP-facing guidance, and user-facing operational documentation.

#### Scenario: User needs to authenticate for XHS publishing
- **WHEN** a user or agent reaches an XHS operation without a valid login state
- **THEN** the documented recovery path MUST direct them to check login status, obtain the upstream login QR code when needed, complete the scan in the Xiaohongshu app, and re-check login state before continuing

### Requirement: Public guidance MUST present the upstream QR-based login flow as the supported user flow
Public skills, usage guides, and public-facing architecture documentation MUST describe the upstream official login status and QR-login workflow as the supported path, including the client-specific QR opening instructions needed when inline image rendering is unavailable.

#### Scenario: Public documentation references XHS login
- **WHEN** a public document or skill explains how to authenticate to Xiaohongshu
- **THEN** it MUST describe the upstream login status and QR-login workflow as the supported path and MUST NOT describe cookie injection as the default public operator flow

### Requirement: Legacy cookie-upload materials MUST be removed or clearly marked as migration/internal-only
If cookie-upload routes, helper functions, or notes remain in the repository for migration, debugging, or staged cleanup, the system documentation SHALL mark them as legacy or internal-only and SHALL separate them from the supported public contract.

#### Scenario: Repository retains cookie-upload-related helpers
- **WHEN** cookie-upload endpoints, handlers, or notes remain in code or docs
- **THEN** those materials MUST be labeled as migration/internal-only and MUST NOT be described as part of the supported public agent workflow
