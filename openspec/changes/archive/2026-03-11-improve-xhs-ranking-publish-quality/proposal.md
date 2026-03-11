## Why

AIInSight's Xiaohongshu ranking publish flow can already produce and publish content, but the current quality bar is still too low for reliable operator use. Recent live validation exposed four classes of problems: MCP/API publish results can diverge in operator-facing semantics, successful publish results do not reliably expose note identifiers, ranking cards are not sufficiently differentiated and may even collide during image persistence, and the default ranking copy/tag composition produces repetitive text and awkward hashtags.

## What Changes

- Improve the XHS ranking publish flow so MCP and API callers receive a consistent publish-result contract, including explicit publish status, login-required state, and propagated note identifier fields when available.
- Add stronger result extraction and raw-result propagation for Xiaohongshu publish responses so successful publishes no longer silently drop `note_url`, `url`, or `post_id` when those fields are present or inferable.
- Harden ranking-card generation and upload preparation so title cards and ranking cards are intentionally differentiated and image persistence cannot accidentally overwrite one rendered card with another.
- Rewrite the default AI daily ranking copy and tag composition flow to remove repeated title/summary text, eliminate duplicate/awkward hashtag output, and generate a more publishable Xiaohongshu ranking post by default.
- Add verification and diagnostics that make runtime-version skew, publish-state mismatch, and QR/login recovery more observable during ranking publish workflows.

## Capabilities

### New Capabilities
- `xhs-publish-result-normalization`: Defines a normalized publish-result contract across API and MCP layers, including identifier propagation, raw-result preservation, and machine-readable failure states.
- `xhs-ranking-publish-quality`: Defines quality requirements for ranking-card differentiation, image persistence uniqueness, and generated ranking copy/tag output.

### Modified Capabilities
- `docker-first-official-xhs-runtime`: Tighten runtime verification expectations so Docker-side XHS publishing reports clearer publish-ready vs login-only states and exposes runtime/version context needed to debug container skew.
- `mcp-tool-schema-compatibility`: Ensure public MCP wrappers for AI Daily publish flows preserve important publish-result fields instead of flattening them into incomplete summaries.

## Impact

- Affected code: `app/services/xiaohongshu_publisher.py`, `app/services/publish/ai_daily_publish_service.py`, `app/services/card_render_client.py`, `app/services/ai_topic_cluster.py`, `app/api/endpoints.py`, `opinion_mcp/tools/ai_daily.py`, `opinion_mcp/tools/publish.py`, and related schemas/tests.
- Affected runtime behavior: ranking publish result shapes, card file persistence, default ranking copy, hashtag composition, login-vs-publish readiness reporting, and MCP/API parity.
- Affected operator experience: users should see clearer post-publish results, more distinct cards, cleaner ranking copy, and more actionable failure information when Docker/XHS runtime state is inconsistent.
