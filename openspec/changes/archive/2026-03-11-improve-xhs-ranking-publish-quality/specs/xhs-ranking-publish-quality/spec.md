## ADDED Requirements

### Requirement: Ranking publish SHALL use distinct cover and ranking cards
The system SHALL generate ranking publish cards so that the title/cover card and the ranking/detail card are visually and semantically distinct enough to avoid being perceived as duplicate ranking boards.

#### Scenario: Default ranking publish generates title and ranking cards
- **WHEN** the system generates default ranking publish cards with `title` and `daily-rank`
- **THEN** the title card MUST function as a cover card with different messaging than the ranking-detail card

### Requirement: Image persistence SHALL prevent uploaded-card overwrites
The system SHALL persist generated ranking publish images using collision-resistant filenames so that distinct rendered images cannot overwrite each other before they are uploaded to Xiaohongshu.

#### Scenario: Two ranking publish cards are persisted in quick succession
- **WHEN** title and ranking card images are written to the shared XHS upload volume during one publish operation
- **THEN** each image MUST be persisted under a unique file path and MUST remain byte-distinct if the rendered images differ

### Requirement: Default ranking copy SHALL suppress repeated title/summary content
The system SHALL avoid emitting repeated title-and-summary lines when a topic summary is empty, equivalent to the title, or too similar to add value.

#### Scenario: Topic summary falls back to title text
- **WHEN** a ranking topic's summary matches or substantially duplicates its title
- **THEN** the default ranking body MUST avoid repeating the same text as both title and summary

### Requirement: Ranking publish SHALL use a single normalized hashtag source
The system SHALL assemble ranking publish hashtags from one normalized source and MUST NOT concatenate hard-coded body hashtags with a second independently generated tag list.

#### Scenario: Ranking publish generates default hashtags
- **WHEN** the system composes a default ranking publish body and tag list
- **THEN** the final published content MUST contain one deduplicated, consistently formatted hashtag block rather than merged or repeated tag sequences

### Requirement: Default ranking copy SHALL remain publishable for mixed-language topics
The system SHALL produce ranking copy that remains readable when some topic summaries are English or low-quality scraped text, using light normalization or fallback phrasing instead of dumping raw truncated text where it adds little value.

#### Scenario: Ranking contains GitHub or English-only topics
- **WHEN** a ranking post includes topics whose summaries are English-only or low-signal raw source text
- **THEN** the default ranking copy MUST normalize or simplify those summaries into a cleaner publishable form
