## Context

The recent Docker-first migration made AIInSight capable of publishing AI daily ranking posts through the official upstream `xhs-mcp` runtime, but live usage exposed a second-order quality problem: “publish works” is not the same as “publish is trustworthy and polished.” The current stack has four distinct issues. First, AI Daily publish results are shaped differently across MCP wrappers and direct API responses, so operators can see inconsistent failure semantics during the same workflow. Second, successful publishes do not reliably surface `note_url` or `post_id`, partly because upstream `xhs-mcp` does not consistently return them and partly because AIInSight does not aggressively preserve or extract whatever identifiers are available. Third, ranking card generation intentionally renders `title` and `daily-rank` cards, but the chosen payloads are semantically too similar and the upload persistence path likely risks filename collision/overwrite. Fourth, the default ranking body/tag generation is too mechanical: titles and summaries repeat, English summaries are pasted almost raw, and body hashtags plus separately selected tags produce awkward final copy.

This change is not another auth/runtime migration. It is a quality and contract-hardening pass on top of the current Docker-first architecture. The goal is to make ranking publish behavior interpretable, resilient, and good enough for repeated operator use.

## Goals / Non-Goals

**Goals:**
- Normalize publish-result semantics across API and MCP wrappers, including richer status and propagated publish identifiers.
- Preserve or infer `note_url`, `url`, and `post_id` whenever upstream returns them structurally or textually, while exposing raw publish results for debugging.
- Ensure title cards and ranking cards are visually/semantically distinct and cannot overwrite each other during shared-volume persistence.
- Produce cleaner, less repetitive ranking copy and a single normalized hashtag source for ranking publish.
- Improve observability around Docker runtime/version skew and publish-ready vs merely logged-in state.

**Non-Goals:**
- Replacing upstream `xhs-mcp` with a custom publishing runtime.
- Guaranteeing that upstream always provides `note_url` or `post_id` after successful publish.
- Redesigning the entire AI Daily topic-ranking algorithm or all card styles in this change.
- Solving every upstream Xiaohongshu publish false-positive case in one pass.

## Decisions

### 1. Publish results should be normalized at the backend integration boundary

The canonical place to normalize XHS publish results is `xiaohongshu_publisher.publish_content`. That function sits directly above the upstream MCP call and below both the API and MCP-facing wrappers. It should produce a stable structure containing success, message, publish status, login-required flags, extracted identifiers, and the raw upstream result.

**Why this decision:** if normalization only happens in outer wrappers, different callers will continue to diverge. The integration boundary is the smallest place where all publish callers benefit.

**Alternatives considered:**
- Normalize only in `opinion_mcp/tools/ai_daily.py`: rejected because direct API callers would still see a different contract.
- Normalize only at the endpoint layer: rejected because non-HTTP callers and deeper services would still receive partial results.

### 2. Identifier extraction should be best-effort and layered

The system should first preserve structured fields from upstream result objects (`note_url`, `url`, `post_id`), then inspect nested `data`, then parse human-readable text content for identifiers as a best-effort fallback. This layered extraction must never invent identifiers, but it should avoid discarding recoverable ones.

**Why this decision:** upstream source and issue history show that publish success is real but payload completeness is inconsistent. Best-effort extraction gives operators the most useful result without pretending the upstream contract is stronger than it is.

**Alternatives considered:**
- Trust only structured fields: rejected because current upstream often omits them.
- Parse only text output: rejected because structured fields should remain the primary source when available.

### 3. Ranking-card quality needs both semantic differentiation and file-persistence hardening

The title card must become a real cover card with different messaging than the ranking card, and the image persistence layer must use content-derived unique filenames (hash/UUID-based) instead of fragile memory/time combinations. Distinct cards that collide during file persistence are still operator-visible duplicates.

**Why this decision:** the user observed both a visual duplication problem and an uploaded-media duplication symptom. These are likely caused by two different but compounding issues: insufficient semantic distance between cards and weak file naming in `_process_image`.

**Alternatives considered:**
- Only change title-card wording: rejected because it would not address upload-time overwrite risk.
- Only change file naming: rejected because the two cards would still feel too similar even if technically distinct.

### 4. Ranking copy should have one summary source and one tag source

Default ranking copy generation must suppress repeated title/summary pairs, apply a lighter-weight rewrite to raw English summaries, and use a single normalized hashtag list at the end of the body. Inline hard-coded hashtags inside the body template should be removed so the tag list has one authoritative source.

**Why this decision:** the current body template and separate tag-selection path both append tag-like content, which guarantees awkward output. Likewise, repeated title/summary pairs are a predictable consequence of `summary_zh` fallback behavior and should be guarded at composition time.

**Alternatives considered:**
- Keep the current body template and only tweak LLM tags: rejected because the duplication starts before tag generation.
- Depend entirely on LLM-generated long-form ranking copy: rejected because the baseline should still be robust when LLM output is limited or unavailable.

### 5. Runtime/version visibility should be part of publish troubleshooting

Docker-first publishing should expose enough build/runtime metadata to tell whether API and MCP containers are aligned, and publish validation should report publish-ready state separately from lightweight login-state checks.

**Why this decision:** the user’s stale-container suspicion was reasonable, and current logs require too much manual correlation to confirm whether version skew is real.

## Risks / Trade-offs

- **[Risk] Best-effort result parsing may still miss identifiers if upstream changes text phrasing** → Mitigation: prefer structured fields first, keep raw result available, and treat regex/text parsing as fallback only.
- **[Risk] Tightening card differentiation could subtly change the visual style users already know** → Mitigation: keep the ranking card renderer intact and limit the title-card changes to cover semantics rather than a full redesign.
- **[Risk] More publish-state diagnostics can expose runtime internals in operator responses** → Mitigation: return concise operator-facing summaries while keeping deeper detail in logs/raw result fields.
- **[Risk] Dedup/rewrite rules could over-trim useful summaries** → Mitigation: start with conservative “summary equals title / highly similar” suppression and add focused tests for edge cases.

## Migration Plan

1. Normalize publish-result extraction at the `xiaohongshu_publisher.publish_content` layer and propagate the richer shape upward.
2. Update API and MCP wrappers so they preserve top-level publish metadata instead of hiding it inside nested payloads.
3. Harden image persistence and adjust ranking cover-card semantics so uploaded cards remain distinct.
4. Rewrite ranking copy/tag assembly to remove duplicated text and unify final hashtag output.
5. Add regression tests for result propagation, file uniqueness, card differentiation, and ranking-copy cleanliness.
6. Validate the full ranking publish flow in Docker and compare API/MCP outputs for the same publish operation.

Rollback would restore the previous result-shaping and ranking-copy/card logic if the new normalization introduces unexpected downstream compatibility issues.

## Open Questions

- Should `note_url` / `post_id` remain top-level fields only, or also live inside a nested `publish_metadata` object for future extensibility?
- How far should English-summary rewriting go in the default ranking body before we cross into “LLM rewrite required” territory?
- Do we want a dedicated third card type for ranking publish later (for example, a “commentary” or “editor note” card), or is a stronger title cover sufficient for now?
