## MODIFIED Requirements

### Requirement: Publish result normalization SHALL preserve and recover identifier fields when available
The system SHALL preserve structured identifier fields from upstream publish results and SHALL attempt best-effort extraction of `note_url`, `url`, and `post_id` from nested payloads or text summaries when the upstream result is incomplete. When no identifier can be recovered, the system SHALL return an explicit user-facing message indicating the publish succeeded but the link is unavailable.

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
- **WHEN** the publish succeeds but no `note_url`, `url`, `post_id`, or `noteId` can be extracted
- **THEN** the result MUST include `note_url: null` and a `message` field containing "已发布成功，但上游未返回 note_url，请在小红书 App 内查看"
