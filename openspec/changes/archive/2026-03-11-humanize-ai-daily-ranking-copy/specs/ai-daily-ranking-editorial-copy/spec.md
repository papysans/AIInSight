## ADDED Requirements

### Requirement: Default whole-ranking publish copy SHALL read like a concise editorial roundup
When no explicit `content` is provided for AI Daily whole-ranking publish, the system SHALL generate a short editorial-style body that summarizes the day as a curated roundup rather than as a raw numbered dump of topic titles and summaries.

#### Scenario: Publish whole ranking without custom content
- **WHEN** a caller invokes the default AI Daily whole-ranking publish flow without supplying `content`
- **THEN** the published body MUST include a concise day-level opening takeaway and supporting observations instead of only repeating ranked topic titles with pasted summaries

### Requirement: Editorial roundup copy SHALL be grounded in observable daily ranking signals
The system SHALL derive editorial roundup wording only from signals observable in the selected AI Daily ranking inputs, such as topic titles, tags, source counts, rank position, source mix, and topic-category cues. It MUST NOT invent momentum, impact, or consensus claims unsupported by the selected topics.

#### Scenario: Ranking contains repeated product-launch and open-source signals
- **WHEN** the selected ranking topics show observable patterns such as multiple launches, open-source projects, research papers, or platform announcements
- **THEN** the default editorial roundup MUST frame those patterns using only the signals present in the ranking inputs rather than unsupported speculation

### Requirement: Editorial roundup copy SHALL use a human-sounding but factual tone
The system SHALL compose default whole-ranking copy in a conversational, operator-like voice that feels human while remaining factual, selective, and concise. It MUST avoid inflated marketing filler, generic “hotspot digest” boilerplate, and exaggerated trend language that cannot be justified by the ranking inputs.

#### Scenario: Generated roundup body is prepared for Xiaohongshu publish
- **WHEN** the system generates default whole-ranking body text for Xiaohongshu publish
- **THEN** the text MUST sound like an informed human summary of the day and MUST avoid generic boilerplate such as mechanically announcing a roundup without any point of view

### Requirement: Editorial roundup copy SHALL degrade gracefully on low-signal days
When the selected topics do not provide enough structured signal for stronger editorial framing, the system SHALL fall back to neutral factual wording that is still readable and publishable. It MUST prefer restrained summary language over noisy pasted fragments or invented conclusions.

#### Scenario: Ranking includes sparse or low-signal summaries
- **WHEN** several selected ranking topics have noisy, English-only, repetitive, or low-information summaries
- **THEN** the default whole-ranking body MUST fall back to cleaner factual phrasing instead of reproducing raw low-signal summary fragments

### Requirement: Explicit whole-ranking publish content SHALL bypass editorial default generation
If a caller supplies explicit `content` for AI Daily whole-ranking publish, the system SHALL preserve that provided body instead of rewriting it through the default editorial-copy generation path.

#### Scenario: Operator provides custom ranking publish body
- **WHEN** `publish_ai_daily_ranking` is called with explicit `content`
- **THEN** the system MUST publish the provided body as-is and MUST NOT replace it with generated editorial roundup text
