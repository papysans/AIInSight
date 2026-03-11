## 1. Ranking editorial-copy generation

- [x] 1.1 Replace the current default whole-ranking body formatter in `app/services/publish/ai_daily_publish_service.py` with a dedicated editorial-copy composition helper used only when `content` is not provided.
- [x] 1.2 Teach the editorial-copy helper to derive 1-2 day-level takeaway themes from the selected ranking topics using observable inputs such as titles, tags, source counts, rank position, and coarse topic categories.
- [x] 1.3 Generate a concise whole-ranking body structure with an opening takeaway plus 2-3 supporting observations anchored to concrete selected topics instead of a raw numbered summary dump.

## 2. Tone rules and fallback behavior

- [x] 2.1 Encode tone constraints for generated whole-ranking copy so it stays conversational, factual, selective, and free of generic marketing filler or unsupported hype.
- [x] 2.2 Add fallback wording rules for low-signal, repetitive, or English-heavy topic inputs so the default body stays readable without pasting noisy raw fragments.
- [x] 2.3 Preserve the existing explicit `content` override path so custom ranking publish body text bypasses the editorial default generator unchanged.

## 3. Verification and regression coverage

- [x] 3.1 Add tests covering the default editorial roundup shape, including a day-level opening takeaway and supporting observations grounded in selected ranking topics.
- [x] 3.2 Add tests proving low-signal inputs degrade to restrained factual copy rather than raw pasted summaries or invented trend claims.
- [x] 3.3 Add tests confirming explicit whole-ranking `content` is preserved exactly and does not get replaced by generated editorial text.

## 4. Output review and operator validation

- [x] 4.1 Run targeted verification for the ranking publish path and capture representative generated outputs for mixed-source AI Daily fixtures.
- [x] 4.2 Review sample outputs to ensure this change improves editorial narration without re-introducing concerns already covered by `improve-xhs-ranking-publish-quality`.
