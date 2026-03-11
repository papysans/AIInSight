## ADDED Requirements

### Requirement: Publish results SHALL expose a normalized contract across API and MCP layers
The system SHALL return a normalized XHS publish-result structure for AI Daily ranking and topic publish flows, regardless of whether the caller uses an HTTP API endpoint or a public MCP wrapper.

#### Scenario: Ranking publish succeeds through API
- **WHEN** an AI Daily ranking publish succeeds through the backend HTTP API
- **THEN** the response MUST include a normalized success flag, publish message, publish status, and any recovered note identifier fields in a predictable shape

#### Scenario: Ranking publish succeeds through MCP
- **WHEN** an AI Daily ranking publish succeeds through an MCP tool wrapper
- **THEN** the MCP result MUST preserve the same normalized publish metadata instead of flattening it into an opaque nested payload only

### Requirement: Publish result normalization SHALL preserve and recover identifier fields when available
The system SHALL preserve structured identifier fields from upstream publish results and SHALL attempt best-effort extraction of `note_url`, `url`, and `post_id` from nested payloads or text summaries when the upstream result is incomplete.

#### Scenario: Upstream publish returns structured identifiers
- **WHEN** the upstream XHS publish result includes `note_url`, `url`, or `post_id` in structured fields
- **THEN** the normalized result MUST expose those fields to downstream callers

#### Scenario: Upstream publish returns only textual success content
- **WHEN** the upstream XHS publish result lacks structured identifier fields but includes a human-readable success summary
- **THEN** the system MUST retain the raw result and MAY expose any best-effort extracted identifiers without inventing values that cannot be recovered

### Requirement: Publish failures SHALL expose machine-readable failure semantics
The system SHALL distinguish login-required, publish-state mismatch, upstream unavailability, and unknown publish failures using machine-readable reason fields that are consistent across API and MCP wrappers.

#### Scenario: Publish fails because login is required
- **WHEN** a ranking or topic publish cannot proceed because the upstream XHS runtime is not publish-ready
- **THEN** the normalized failure result MUST expose login-required state and a reason code that callers can interpret consistently
