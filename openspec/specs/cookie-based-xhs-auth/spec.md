## ADDED Requirements

### Requirement: Cookie injection is the only supported public XHS login flow
The system SHALL define browser-side cookie extraction plus cookie injection as the only supported public authentication flow for Xiaohongshu operations exposed through skills, MCP-facing guidance, and user-facing operational documentation.

#### Scenario: User needs to authenticate for XHS publishing
- **WHEN** a user or agent reaches an XHS operation without a valid login state
- **THEN** the documented recovery path MUST direct them to obtain cookies from a real browser session and inject them through the supported cookie-upload flow

### Requirement: Public guidance MUST NOT present QR login as a supported user flow
Public skills, usage guides, and public-facing architecture documentation MUST NOT present QR-code login as an active supported workflow for agent-driven XHS authentication.

#### Scenario: Public documentation references XHS login
- **WHEN** a public document or skill explains how to authenticate to Xiaohongshu
- **THEN** it MUST describe the cookie-injection workflow as the supported path and MUST NOT describe QR login as a recommended or default option

### Requirement: Legacy QR login materials MUST be removed or clearly marked as internal-only
If QR-login routes, helper functions, or notes remain in the repository for debugging or staged cleanup, the system documentation SHALL mark them as internal-only or legacy and SHALL separate them from the supported public contract.

#### Scenario: Repository retains QR-related helpers
- **WHEN** QR-related endpoints, handlers, or notes remain in code or docs
- **THEN** those materials MUST be labeled as legacy/internal and MUST NOT be described as part of the supported public agent workflow
