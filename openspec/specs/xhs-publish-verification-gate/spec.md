## ADDED Requirements

### Requirement: Publish verification gate SHALL confirm noteId via creator center before returning success
The system SHALL, after upstream `publishContent()` returns, query the creator center (`getMyPublishedNotes`) to verify that a note with the matching title was actually published. Only when a matching note is found SHALL the system return `success: true` with the verified `noteId` and `noteUrl`.

#### Scenario: Upstream returns noteId directly
- **WHEN** upstream `publishContent()` returns `{ success: true, noteId: "<id>" }`
- **THEN** the system MUST trust the noteId, record it in DB, and return `{ success: true, noteId, noteUrl }` without additional verification

#### Scenario: Upstream returns success without noteId (common case)
- **WHEN** upstream returns `{ success: true }` with no `noteId`
- **THEN** the system MUST wait 5 seconds for platform sync, then query creator center for the 10 most recent notes
- **AND** match by exact title within a 3-minute publish window
- **AND** if matched, return `{ success: true, noteId, noteUrl, verifiedVia: "creator_center" }`

#### Scenario: Verification finds no matching note
- **WHEN** creator center query returns no note matching the title within the time window
- **THEN** the system MUST return `{ success: false, error: "submitted_but_unverified" }` with a user-facing message

#### Scenario: Creator center query fails or times out
- **WHEN** the creator center query throws an exception or exceeds 15 seconds
- **THEN** the system MUST return `{ success: false, error: "submitted_but_unverified" }` — MUST NOT return a false success

### Requirement: Unverified publishes SHALL NOT be recorded in the published database
The system SHALL only call `db.published.record()` when a noteId has been confirmed (either from upstream or via creator center verification). Unverified publishes MUST NOT be written to the database.

#### Scenario: Verified publish records to DB
- **WHEN** a noteId is confirmed via either upstream response or creator center
- **THEN** the system MUST call `db.published.record()` with the verified noteId and status `published` or `scheduled`

#### Scenario: Unverified publish skips DB record
- **WHEN** verification fails and no noteId can be confirmed
- **THEN** the system MUST NOT call `db.published.record()`
