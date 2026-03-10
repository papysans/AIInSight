## Context

AIInSight currently has one real XHS operator flow and several older traces of previous experiments. The real working path is browser-side login in a real user environment, followed by cookie extraction and cookie injection through the backend. However, the repository still contains QR-login-oriented docs, endpoints, comments, and internal helper functions that make the public contract look broader than it should be. This creates confusion for MCP consumers and for future maintenance.

At the same time, the MCP server exposes tool schemas manually. That gives the project flexibility, but it also means schema mistakes become public compatibility failures. The current `upload_xhs_cookies` schema attempts to express multiple input formats in a way that is not safe for all downstream MCP/OpenAI-style consumers.

Finally, `analyze_ai_topic` is intended to analyze AI Daily topics, but its MCP path currently degrades topic context by flattening the topic into plain text before routing into the generic analysis flow. The dedicated AI Daily HTTP path already preserves richer topic structure and should inform the MCP behavior.

## Goals / Non-Goals

**Goals:**
- Make cookie injection the only supported public XHS login path in skills, docs, and MCP-facing guidance.
- Remove or demote QR-login materials from the supported user flow without breaking internal/private helper code that is still useful for diagnostics.
- Ensure all public MCP tool schemas are valid and compatible with downstream consumers, especially tools that currently expose mixed-type payloads.
- Improve `analyze_ai_topic` so AI Daily topic analysis preserves structured topic context and produces results closer to the dedicated AI Daily analysis behavior.
- Clarify the public MCP surface so skills and docs describe only the officially supported tools and payloads.

**Non-Goals:**
- Rebuilding the XHS publishing subsystem or replacing cookie injection with a new login strategy.
- Reworking the entire generic topic analysis workflow for arbitrary non-AI-Daily topics.
- Deleting every legacy helper immediately if it is still useful for direct HTTP debugging or internal maintenance.
- Introducing a new frontend workbench or redesigning card rendering as part of this change.

## Decisions

### 1. Treat cookie injection as the only supported public XHS authentication contract

The system will define a single supported operator story: user logs into Xiaohongshu in a real browser, extracts cookies, and provides them for injection. Skills, usage guides, architecture docs, and MCP tool guidance will all align to this path. QR-login references will either be removed from user-facing guidance or clearly marked as legacy/internal-only.

**Why this decision:** it reflects the confirmed real-world working path and removes ambiguity for operators and agent consumers.

**Alternatives considered:**
- Keep dual official login paths (QR + cookies): rejected because QR is no longer reliable enough to remain a first-class public path.
- Delete every QR-related code path immediately: rejected because some endpoints/helpers may still be useful for diagnostics or staged cleanup.

### 2. Public MCP schemas must target downstream compatibility first, not maximum type flexibility

For public MCP tools, schemas will use consumer-safe JSON Schema shapes. Mixed-format inputs such as cookies should be represented in a way that does not produce invalid OpenAI-compatible function schemas. If necessary, the public contract should narrow to the most common supported input shape and let backend normalization preserve flexibility internally.

This means public MCP tool definitions should be reviewed centrally in `opinion_mcp/server.py`, with a bias toward explicit, stable schemas over permissive but fragile ones.

**Why this decision:** the current failure is happening at tool discovery time, so public compatibility matters more than advertising every tolerated backend input variant.

**Alternatives considered:**
- Keep permissive union-like schemas for all public tools: rejected because downstream clients may reject them before execution.
- Generate all schemas dynamically from backend/Pydantic models: rejected for this change because the immediate need is to stabilize exposed MCP contracts, not refactor the whole schema-generation stack.

### 3. `analyze_ai_topic` should preserve AI Daily topic structure instead of flattening to plain text too early

The MCP `analyze_ai_topic` path should align with the higher-fidelity AI Daily analysis behavior. Instead of reducing a topic to `title + summary`, it should preserve structured topic context such as source items, summaries, tags, and any reusable cached evidence that already exists in the AI Daily pipeline.

There are two acceptable implementation directions:
- call the dedicated AI Daily analysis backend path directly from MCP, or
- reuse the same adapter logic used by the HTTP AI Daily analyze path so MCP and HTTP share the same topic-to-workflow conversion.

The preferred direction is whichever yields one canonical AI Daily topic-analysis path with minimal duplication.

**Why this decision:** current MCP analysis loses context that the HTTP AI Daily path already knows how to preserve.

**Alternatives considered:**
- Keep the current text-flattened MCP path: rejected because it weakens fidelity for AI Daily topics.
- Merge all analysis paths into one generic workflow immediately: rejected as too large for this change.

### 4. Public contract cleanup should distinguish between exposed MCP tools and internal helper handlers

The repository should make a sharper distinction between:
- tools in the public MCP tool list,
- internal handlers that are callable only through direct HTTP/debug paths,
- historical or deprecated routes/materials.

Docs and skill guidance should describe only the public contract unless a section is explicitly marked as internal or legacy.

**Why this decision:** most confusion comes from readers treating `TOOL_HANDLERS`, helper functions, and architecture notes as if they were the same thing as the public MCP surface.

## Risks / Trade-offs

- **[Risk] Narrowing public schemas may reduce some previously tolerated tool payload shapes** → Mitigation: keep backend normalization tolerant while stabilizing the public MCP shape around the officially recommended payload.
- **[Risk] Removing or demoting QR-login docs may surprise maintainers who still use those helpers internally** → Mitigation: label any retained endpoints/helpers as internal or legacy instead of silently deleting useful diagnostics.
- **[Risk] Aligning MCP analysis with the AI Daily path may change result content or timing** → Mitigation: explicitly compare result shape, latency expectations, and user flow before switching the MCP path.
- **[Risk] Partial cleanup could leave skills, docs, and tool definitions drifting again** → Mitigation: treat this as one contract-cleanup change covering code, docs, and skills together.

## Migration Plan

1. Stabilize the public MCP schema contract, starting with `upload_xhs_cookies` and any adjacent login-related tools.
2. Update skills and docs so cookie injection is the only supported login path in public guidance.
3. Demote QR-login references to internal/legacy status or remove them where they no longer serve a supported use case.
4. Refactor `analyze_ai_topic` to align with the canonical AI Daily topic-analysis path.
5. Verify MCP tool discovery works in downstream clients and that AI Daily topic analysis still produces complete outputs.

Rollback is straightforward for documentation and skill changes. For MCP analysis-path changes, rollback should restore the previous MCP wrapper behavior if compatibility or latency regressions appear.

## Open Questions

- Should `upload_xhs_cookies` publicly accept only raw cookie strings, or should it still expose a multi-format contract in a safer schema form?
- Should QR-login HTTP endpoints remain in the repo as internal/debug-only routes, or should they be removed entirely in this change?
- For `analyze_ai_topic`, is the preferred canonical path direct backend AI Daily analysis, or shared adapter reuse inside MCP?
