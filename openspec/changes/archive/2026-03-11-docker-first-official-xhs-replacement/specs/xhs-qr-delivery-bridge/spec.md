## ADDED Requirements

### Requirement: QR login responses SHALL provide a non-inline access path for operators
When the system obtains an XHS login QR code from the upstream official login tool flow, it SHALL make that QR artifact available through at least one operator-accessible non-inline path such as a served URL or file path.

#### Scenario: Client cannot render MCP QR image inline
- **WHEN** an operator uses a client that does not display the returned QR image content directly
- **THEN** the system MUST return enough metadata for the operator to open the QR manually, including a served URL and/or local file path

### Requirement: QR delivery guidance SHALL remain aligned with the official login tool sequence
The system SHALL preserve the upstream official login sequence while adapting only the QR presentation instructions for clients that cannot render images inline.

#### Scenario: Operator starts official login flow through local guidance
- **WHEN** the operator follows the supported login instructions in OpenCode or Claude Code
- **THEN** the instructions MUST still follow `check_login_status` → `get_login_qrcode` → scan → `check_login_status`, with the only adaptation being how the QR artifact is opened or displayed

### Requirement: Scan-required state SHALL notify the operator explicitly
Whenever a publish or validation workflow cannot proceed until a QR code is scanned, the system SHALL stop and notify the operator that manual scanning is required.

#### Scenario: Verification reaches a login-required checkpoint
- **WHEN** the system detects that XHS login is required during validation or publish preflight
- **THEN** it MUST report a login-required state and instruct the operator to complete the scan before verification continues
