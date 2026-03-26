## MODIFIED Requirements

### Requirement: Publish result normalization SHALL preserve and recover identifier fields when available
The system SHALL preserve structured identifier fields from upstream publish results and SHALL attempt best-effort extraction of `note_url`, `url`, and `post_id` from nested payloads or text summaries when the upstream result is incomplete. When no identifier can be recovered, the system SHALL return `success: false` with error code `submitted_but_unverified`.

#### Scenario: Upstream publish returns structured identifiers
- **WHEN** the upstream XHS publish result includes `note_url`, `url`, or `post_id` in structured fields
- **THEN** the normalized result MUST expose those fields to downstream callers

#### Scenario: Upstream publish returns only textual success content
- **WHEN** the upstream XHS publish result lacks structured identifier fields but includes a human-readable success summary
- **THEN** the system MUST retain the raw result and MAY expose any best-effort extracted identifiers without inventing values that cannot be recovered

#### Scenario: Upstream publish returns noteId but not note_url
- **WHEN** the upstream XHS publish result includes `noteId` but no `note_url`
- **THEN** the system MUST construct a `note_url` from the `noteId` using the pattern `https://www.xiaohongshu.com/explore/{noteId}`

#### Scenario: No identifier can be recovered from successful publish
- **WHEN** the upstream reports success but no `note_url`, `url`, `post_id`, or `noteId` can be extracted
- **THEN** the result MUST return `success: false` with `error: "submitted_but_unverified"` and `note_url: null`
- **AND** MUST include a `message` field containing user-facing guidance to check manually in the XHS App
