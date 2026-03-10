## 1. Cookie-only XHS auth contract cleanup

- [x] 1.1 Inventory and remove or demote QR-login references from public-facing docs, skills, and usage guidance so cookie injection is the only supported public login path.
- [x] 1.2 Update any retained QR-related endpoints, comments, or helper notes to be explicitly labeled as legacy/internal-only where they remain for diagnostics.
- [x] 1.3 Align AI Insight skill guidance and XHS operational docs with the cookie-extraction-and-injection workflow, including consistent field names and supported user steps.

## 2. MCP public schema and contract hardening

- [x] 2.1 Audit the public `MCP_TOOLS` definitions in `opinion_mcp/server.py` and identify schema shapes that are unsafe for downstream MCP/OpenAI-compatible consumers.
- [x] 2.2 Replace the exposed `upload_xhs_cookies` public schema with a downstream-compatible contract while keeping backend normalization tolerant of the supported cookie input format.
- [x] 2.3 Align MCP tool descriptions, public docs, and skill guidance so only actually exposed tools and their real argument contracts are described as public MCP capabilities.

## 3. AI Daily topic analysis path alignment

- [x] 3.1 Trace the current `analyze_ai_topic` MCP path against the dedicated AI Daily HTTP analysis path and choose one canonical topic-context-preserving route.
- [x] 3.2 Refactor `analyze_ai_topic` to preserve structured AI Daily topic context rather than flattening the topic to title-plus-summary text too early.
- [x] 3.3 Update any related response handling or user guidance so MCP AI Daily analysis still fits the expected topic-first analysis workflow.

## 4. Verification and regression checks

- [x] 4.1 Verify public MCP tool discovery succeeds in a downstream-compatible client after schema cleanup, especially for `upload_xhs_cookies`.
- [x] 4.2 Verify AI Daily topic analysis through the supported MCP path still produces complete results and remains aligned with the dedicated HTTP AI Daily analysis fidelity.
- [x] 4.3 Run targeted documentation and contract review so public guidance, exposed tool lists, and implementation behavior all describe the same supported login and analysis paths.
