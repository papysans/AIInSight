# AIInSight vs main — Implementation Diff Summary

Date: 2026-03-25
Base: `main`
Scope summary: **87 files changed, 7518 insertions(+), 1305 deletions(-)**

## Executive Summary

This branch delivers three major architecture outcomes on top of `main`:

1. **ShunL XHS runtime integration and publish-path hardening**
2. **Cloud remote gateway split + multi-account backend core**
3. **A new host-controlled analysis pipeline foundation**

The result is a system that can:

- use ShunL `xhs-mcp` as the XHS runtime,
- run split analysis workflows (`retrieve_and_report` / `submit_analysis_result`),
- isolate jobs, settings, artifacts, and credentials by account,
- expose API-key based gateway identity and admin endpoints,
- and start moving the full analysis chain to the host via a local MCP entrypoint.

---

## 1. XHS Runtime and Publish Path

### What changed

- Replaced the previous XHS sidecar assumptions with **ShunL xhs-mcp** integration.
- Added/updated Docker runtime assets for the new XHS path:
  - `Dockerfile.xhs-mcp`
  - `xhs-mcp-entrypoint.mjs`
  - `docker-compose.yml`
  - `docker-compose.xhs.yml`
- Reworked `app/services/xiaohongshu_publisher.py` to:
  - align with ShunL tool names and response formats,
  - support account-aware XHS state,
  - fix login status parsing,
  - normalize inner publish failures correctly,
  - and support the final publish path used by AI Daily and topic publishing.
- Updated XHS-related MCP tools:
  - `opinion_mcp/tools/publish.py`
  - `opinion_mcp/services/xiaohongshu_publisher.py` (直连 xhs-mcp，不再经 backend_client 中转)

### Why it matters

- The branch removes the old brittle publish behavior and makes the XHS path compatible with the current ShunL runtime.
- It also lays the foundation for per-account XHS state under the remote gateway model.

---

## 2. Remote Gateway Split Analysis Path

### What changed

- Added split backend workflow helpers in `app/services/workflow.py`:
  - `run_retrieve_and_report(...)`
  - `run_submit_analysis_result(...)`
- Added new backend API endpoints in `app/api/endpoints.py`:
  - `POST /api/retrieve-and-report`
  - `POST /api/submit-analysis-result`
- Added MCP-side support in:
  - `opinion_mcp/services/backend_client.py`
  - `opinion_mcp/tools/analyze.py`
  - `opinion_mcp/tools/__init__.py`
  - `opinion_mcp/server.py`
- Preserved the old full-path compatibility route:
  - `analyze_topic`
  - `POST /api/analyze`

### Important behavior fix

- `writer_node` now actually consumes the upstream analysis result instead of silently ignoring it.
- `retrieve_and_report` now supports a bounded `evidence_mode=summary` option.
- Split endpoints now have explicit timeout guards.

### Why it matters

- This turns the backend into a usable split workflow surface instead of a single monolithic analyze path.
- It also provides the migration bridge for host-side reasoning.

---

## 3. Account Identity, Multi-Account State, and Admin Auth

### Identity propagation

Added request-scoped account context to both backend and MCP layers:

- `app/services/account_context.py`
- `opinion_mcp/services/account_context.py`
- backend middleware in `app/main.py`
- gateway middleware and request resolution in `opinion_mcp/server.py`

### API key registry and admin surface

- Added `opinion_mcp/services/api_key_registry.py`
- Added gateway-side admin endpoints:
  - `POST /admin/api-keys`
  - `GET /admin/api-keys`
  - `POST /admin/api-keys/revoke`
- Added optional strict auth mode via config:
  - `OPINION_REQUIRE_API_KEY`

### Per-account state isolation

- `opinion_mcp/services/job_manager.py`
- `opinion_mcp/services/webhook_manager.py`
- `app/services/workflow_status.py`
- `app/services/user_settings.py`

These now partition state by `account_id` instead of treating the process as single-tenant.

### Why it matters

- The branch converts the gateway/backend from a single shared workspace into a per-account system.
- This is the core enabler for any real cloud-hosted multi-user deployment.

---

## 4. Artifact and Output Isolation

### What changed

- Markdown outputs now write under account-scoped directories.
- Card previews are account-scoped.
- XHS QR / preview metadata paths are account-scoped.
- `/outputs` and related artifact-serving routes now resolve through account context.

Primary files:

- `app/services/workflow.py`
- `app/services/card_render_client.py`
- `app/api/endpoints.py`
- `app/services/xiaohongshu_publisher.py`

### Why it matters

- Users no longer share output files and preview surfaces by default.
- This makes the remote gateway safer and less state-leaky.

---

## 5. Credential Isolation and Key Rotation

### What changed

- User settings are now stored per account.
- Effective LLM key selection is account-aware.
- Volcengine credential resolution is account-aware.
- LLM key rotation is partitioned by `(account, provider)` instead of provider only.

Primary files:

- `app/services/user_settings.py`
- `app/llm.py`

### Why it matters

- Different users can use different LLM/API credentials safely inside the same backend process.
- Rotation state is no longer shared across accounts.

---

## 6. Host-Controlled Analysis Pipeline Foundation

### What changed

Added a new host-oriented analysis module:

- `app/services/host_analysis_pipeline.py`

It now includes:

- host-side source resolution,
- host-side evidence retrieval orchestration,
- a local evidence/analysis state,
- a host reasoning loop,
- default host reporter / analyst / debater / writer,
- renderer/publish/artifact contract builders,
- a default host capability bridge,
- and a top-level `run_default_host_analysis(...)` executor.

Added new host entrypoints:

- `host_analyze_topic` in `opinion_mcp/tools/analyze.py`
- `host_analyze_ai_topic` in `opinion_mcp/tools/ai_daily.py`

Both are now exposed through the MCP surface.

### Why it matters

- The branch doesn’t just define the host-controlled architecture on paper; it starts implementing it in code.
- It gives the repo a second analysis model beyond the cloud workflow: local host orchestration with cloud capability services.

---

## 7. Skills and Documentation Alignment

### Updated public guidance

- `README.md`
- `.agents/skills/ai-topic-analyzer/SKILL.md`
- `.agents/skills/ai-insight/SKILL.md`
- `docs/XHS_MCP_Architecture.md`

### What changed in docs

- Clarified local/self-hosted vs remote gateway modes.
- Documented split analysis path and host-side debate flow.
- Documented account-aware remote gateway assumptions.
- Documented the newer XHS runtime expectations.

---

## 8. OpenSpec Artifacts Added or Updated

### New / updated change sets

- `openspec/changes/shunl-xhs-mcp-integration/`
- `openspec/changes/cloud-remote-mcp-gateway/`
- `openspec/changes/host-controlled-analysis-pipeline/`
- `openspec/changes/archive/2026-03-24-shunl-xhs-mcp-bugfixes/`

### Why it matters

- The branch contains both implementation work and the spec/design/task records that explain the migration path.

---

## 9. Verification Summary

Focused verification completed on:

- workflow split contracts
- endpoint split contracts
- MCP split contracts
- account identity propagation
- API key registry and admin endpoints
- readiness/health server surface
- artifact path isolation
- credential isolation
- outputs isolation
- LLM rotation isolation
- legacy analyze path compatibility
- host-controlled pipeline
- host pipeline migration compatibility
- host MCP entrypoint(s)
- XHS runtime/publish regressions
- AI Daily publish regressions

Representative result: **48+ focused tests passing** across the new and modified surfaces during this branch’s development.

---

## 10. Remaining Work (Non-Core-Code)

What remains after this branch is mostly **deployment / ops / rollout** work rather than missing core implementation, for example:

- real cloud deployment validation
- rollback and canary procedures
- dual-account live environment verification
- production rate limiting / richer auditing / observability
- long-lived cache strategy decisions

Those are important, but they are no longer blockers for understanding what the branch changed at the code/architecture level.
