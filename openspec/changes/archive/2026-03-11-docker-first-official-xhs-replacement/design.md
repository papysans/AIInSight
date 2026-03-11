## Context

AIInSight currently contains three overlapping Xiaohongshu stories: a host-side `xhs-mcp` recommendation, a cookie-upload-first public contract, and leftover QR/Playwright helper paths. The upstream official projects are simpler conceptually: `xiaohongshu-mcp` is the runtime, `xiaohongshu-mcp-skills` is the instruction layer, Docker is documented as a first-class deployment mode, and login is centered on `check_login_status`, `get_login_qrcode`, and `delete_cookies`. However, the upstream Docker docs assume a client such as MCP Inspector can display the QR image directly, while OpenCode/Claude Code may not reliably surface that image content to the operator.

The new change tightens the migration goal rather than hedging it. There will be no supported host-side `xhs-mcp` fallback in the plan. The primary chain becomes: AIInSight services + `xhs-mcp` sidecar in Docker, official upstream login semantics, and an AIInSight-owned QR delivery adaptation that converts upstream QR responses into stable URLs/file paths the operator can open outside the MCP image-rendering path when necessary. This means the migration is both a contract change and a topology decision.

## Goals / Non-Goals

**Goals:**
- Make Docker the primary and only supported XHS runtime topology for this migration.
- Align AIInSight login and operator flow with the official upstream XHS MCP skills contract.
- Provide a reliable QR delivery path for clients that cannot render MCP image payloads inline.
- Remove host-side and cookie-upload-first guidance from the supported public contract.
- Keep verification explicit so the system can stop, report login-required state, and notify the operator when scanning is necessary.

**Non-Goals:**
- Preserving host-side `xhs-mcp` as an officially supported fallback path.
- Maintaining raw cookie injection as a first-class public login workflow.
- Replacing upstream Docker behavior with a completely separate AIInSight-authored login runtime.
- Solving every possible upstream Docker instability through this design alone.

## Decisions

### 1. Docker sidecar is the supported XHS runtime, not an optional overlay

The supported XHS topology will become a Docker-first chain in which `xhs-mcp` runs as a sidecar service and AIInSight services talk to it over the Docker network. Public docs and implementation assumptions will target `http://xhs-mcp:18060/mcp` rather than a host-side MCP URL.

**Why this decision:** the user explicitly wants full Dockerization and no host-side path in the plan.

**Alternatives considered:**
- Keep host-side runtime as the stable default: rejected by user requirement.
- Support both host and Docker as equal first-class paths: rejected because it would dilute the migration and preserve split behavior.

### 2. Official upstream login semantics stay intact, but QR delivery is adapted for non-rendering clients

AIInSight will preserve the upstream public tool semantics (`check_login_status`, `get_login_qrcode`, `delete_cookies`) and official skill flow, but will adapt the QR presentation layer. When `get_login_qrcode` returns image content, AIInSight will persist the PNG, expose a stable HTTP route and absolute URL, and include file-path metadata so OpenCode/Claude Code users can open the QR manually if inline rendering is unavailable.

**Why this decision:** it keeps the official auth contract while solving the real client limitation you called out.

**Alternatives considered:**
- Rewrite the official skill to fall back to cookie upload: rejected because it breaks the upstream-official direction.
- Depend on inline image rendering only: rejected because it fails in some target clients.

### 3. Local skills/guidance may be lightly adapted, but only at the presentation layer

The local adaptation will stay close to `xiaohongshu-mcp-skills`. The only intentional divergence will be client-oriented instructions such as “if the QR image does not render inline, open `qr_image_url` or the served file route.” Tool names, sequencing, and login semantics should remain upstream-aligned.

**Why this decision:** it gives the operator a usable flow without creating a separate auth contract.

**Alternatives considered:**
- Copy official skills verbatim: rejected because that would ignore known client UX gaps.
- Build a brand-new custom local login skill: rejected because it would increase drift from upstream.

### 4. Existing cookie-upload and host-oriented helpers become migration/legacy surfaces only

Any retained cookie-upload endpoints, login-v2 Playwright paths, or host-side helper scripts must be treated as migration/internal-only and removed from the supported public workflow. The new public story must be singular: Docker sidecar + official upstream login semantics + QR delivery bridge.

**Why this decision:** otherwise the migration would leave contradictory instructions in place.

## Risks / Trade-offs

- **[Risk] Upstream Docker QR login may still be flaky in some environments** → Mitigation: make Docker health/login verification explicit, document platform constraints, and keep scan-required handling operator-visible rather than silent.
- **[Risk] Removing host-side guidance increases pressure on the Docker path to work well** → Mitigation: prioritize end-to-end Docker verification and make image/platform requirements part of the contract.
- **[Risk] QR URL/file-path bridging may expose more moving pieces (public base URL, file serving, cleanup)** → Mitigation: reuse the repo's existing QR persistence and file-serving pattern instead of inventing a new storage mechanism.
- **[Risk] Local skills can drift from upstream again** → Mitigation: keep only the minimal QR presentation adaptation and preserve upstream tool order and semantics.

## Migration Plan

1. Rewrite the public XHS contract in specs/docs from host-or-cookie-first to Docker-first official upstream runtime.
2. Update compose/runtime configuration so `xhs-mcp` sidecar is the supported chain and host-side guidance is removed.
3. Refactor XHS status/login/publish code to use the official upstream login semantics as the public path.
4. Adapt local skills and API responses to always provide QR URL/file-path fallbacks when inline image rendering is insufficient.
5. Remove or demote host-side and cookie-upload public guidance to migration/internal-only status.
6. Verify the full Docker chain end-to-end, including a real scan-required checkpoint.

Rollback would restore the previous host-side/cookie-first public contract and related docs/endpoints if the Docker-first official path proves unacceptable.

## Open Questions

- Should QR artifacts be exposed only through authenticated AIInSight routes, or is a plain served URL sufficient in the initial migration?
- Do we want to keep the existing Playwright login-v2 route as an internal diagnostic path, or remove it entirely once the official QR bridge is in place?
- Should local skill docs instruct users to open `qr_image_url`, `qr_image_route`, or both when inline rendering fails?
