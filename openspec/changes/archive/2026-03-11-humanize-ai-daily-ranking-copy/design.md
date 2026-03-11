## Context

The current AI Daily whole-ranking publish flow already has a stable path for collecting topics, generating cards, and publishing to Xiaohongshu, but its default body copy is still assembled like a bulletin. In `app/services/publish/ai_daily_publish_service.py`, `_default_ranking_content()` currently combines the date, top topic titles, and truncated `summary_zh` text into a fixed template. That means the final post inherits all the weaknesses of `summary_zh`: it can be repetitive, too literal, mixed-language, or too low-signal to sound like a real person summarizing the day.

This change is not about replacing ranking cards, changing the ranking algorithm, or forcing a long-form LLM generation path for every publish. It is a focused upgrade to the default ranking-copy composition layer so the system can express the day's biggest AI themes in a brief, conversational, operator-friendly voice while staying grounded in the selected topics. The main stakeholders are operators using the AI Daily publish flow and end readers on Xiaohongshu who need an immediate sense of “what mattered today” rather than a raw list of scraped summaries.

This design intentionally stays narrower than the earlier `improve-xhs-ranking-publish-quality` change. That earlier work covers publishability hygiene such as duplicate-summary suppression, hashtag normalization, and ranking publish quality more broadly. This change only defines how the whole-ranking body should sound like a short, grounded editorial roundup built from today's AI hotspot signals.

## Goals / Non-Goals

**Goals:**
- Generate default whole-ranking publish copy as a short editorial summary instead of a title-and-summary dump.
- Base that copy on structured daily topic context so it reflects repeated themes and notable daily signals across the selected topics.
- Keep the tone conversational, selective, and factual enough to feel human without turning into hype or unsupported opinion.
- Define deterministic fallback behavior for noisy, repetitive, or English-only topic summaries.
- Preserve the current publish API shape so callers can still override `content` manually when needed.

**Non-Goals:**
- Replacing the existing ranking card renderers or adding new card types in this change.
- Rebuilding the AI Daily clustering or topic scoring pipeline.
- Requiring an expensive deep-analysis workflow for every ranking publish.
- Turning the publish flow into an unrestricted long-form copywriting system.
- Re-specifying hashtag normalization, duplicate-summary cleanup, card distinctness, or publish-result normalization already covered elsewhere.

## Decisions

### 1. Add a dedicated ranking editorial-copy composition step

The default `publish_ai_daily_ranking` path should stop using `_default_ranking_content()` as a simple formatter and instead call a dedicated composition helper that produces a short editorial-style body from the selected topics. That helper should still operate on the top ranking topics already chosen for publish, so it remains aligned with the ranking cards and current publish semantics.

**Why this decision:** the current problem sits at the final composition layer, not in transport or rendering. A dedicated helper gives us one place to encode tone, structure, and fallback rules without disturbing callers that already pass custom `content`.

**Alternatives considered:**
- Reuse the deep-analysis writer workflow directly for every ranking publish: rejected because it adds cost and latency to a path that should stay lightweight.
- Keep the current template and only tweak wording: rejected because a static formatter still cannot summarize cross-topic daily themes like a human editor would.

### 2. Use structured topic signals to derive a day-level takeaway before listing supporting points

The new copy helper should first infer 1-2 high-level themes from the selected topics, such as open-source momentum, model competition, tooling adoption, research acceleration, or platform moves. It should then use those themes to generate an opening sentence and 2-3 concise supporting observations anchored in actual ranked topics.

**Why this decision:** what makes the copy feel human is not slang; it is the presence of a day-level point of view. A human operator usually notices a pattern first and then cites examples. Encoding that same structure makes the output feel less mechanical while remaining explainable.

**Alternatives considered:**
- Summarize each ranked topic independently in fixed bullets: rejected because it recreates the current “list of fragments” problem.
- Generate purely free-form commentary without structured inputs: rejected because it risks drifting away from the real daily topics.

### 3. Constrain tone with explicit editorial rules instead of open-ended creative writing

The new default body should follow explicit rules: brief first-sentence takeaway, concrete references to named topics or signals, mild human judgment, and no inflated marketing filler. The tone target should be “an informed friend who did the homework,” not brand copy and not exaggerated clickbait.

**Why this decision:** the user's complaint is specifically about copy sounding too plain, not about needing a flashy viral style. Editorial constraints make the output more consistent and easier to test.

**Alternatives considered:**
- Ask the LLM for “more human” wording with no structure: rejected because that is hard to validate and tends to drift into empty enthusiasm.
- Avoid any style rules and trust source summaries: rejected because raw summaries are the original problem.

### 4. Keep deterministic fallbacks for low-signal topics and limited generation quality

If the system cannot confidently derive themes or if some topic summaries are too noisy, the helper should fall back to a lighter-weight structured template that still avoids raw duplication. That fallback should prefer normalized short descriptions based on topic titles, tags, source counts, and coarse topic categories instead of directly pasting truncated source summaries.

**Why this decision:** the default path must remain publishable even when source text quality is weak or generation fails. A stronger fallback keeps reliability high without regressing to the current awkward text dump.

**Alternatives considered:**
- Hard-fail when higher-quality composition cannot run: rejected because publish should degrade gracefully.
- Always paste `summary_zh` when generation is weak: rejected because that reproduces the same operator-visible problem.

### 5. Keep manual `content` override semantics unchanged

If a caller passes `content`, the system should continue using that text exactly as provided. The editorial-copy helper only changes the default branch where no explicit content is supplied.

**Why this decision:** existing operators may already use custom publish copy, and this change should improve defaults without narrowing current control.

**Alternatives considered:**
- Always rewrite provided content into the new tone: rejected because it would surprise callers and break expectation of explicit overrides.

## Risks / Trade-offs

- **[Risk] Theme extraction could over-generalize the day and flatten important niche stories** → Mitigation: keep supporting points anchored to concrete ranked topics and cap abstraction to 1-2 day-level themes.
- **[Risk] “Human” tone could drift into hype or unsupported judgment** → Mitigation: define style rules that require factual grounding and ban generic marketing filler.
- **[Risk] Fallback logic may still sound templated on low-signal days** → Mitigation: prefer concise but clean fallback copy over noisy summaries, and test with mixed-language / sparse-topic fixtures.
- **[Risk] New copy behavior may partially overlap existing ranking-publish-quality work** → Mitigation: scope this change to editorial summary generation and day-level framing, not generic deduplication or hashtag normalization alone.

## Migration Plan

1. Introduce the new editorial-copy helper behind the existing default branch for `publish_ai_daily_ranking`.
2. Reuse current selected topics and metadata as inputs, without changing request/response schema for callers.
3. Add regression coverage for conversational opening, theme grounding, fallback behavior, and manual content override.
4. Compare generated outputs on representative AI Daily fixtures to ensure the new default reads more like an editorial roundup than a scraped digest.
5. Roll back by restoring the previous `_default_ranking_content()` path if the new composition logic causes unacceptable tone drift or instability.

## Open Questions

- Should the day-level theme extraction stay fully deterministic at first, or should it immediately use a lightweight LLM summarization step with structured guardrails?
- Do we want one fixed editorial structure for every day, or a small set of allowed variations to avoid copy becoming formulaic again?
- Should future work extend the same editorial-copy logic to single-topic AI Daily publish content, or keep this change strictly focused on whole-ranking posts?
