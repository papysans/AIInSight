## 1. Docker-first runtime migration

- [x] 1.1 Replace host-side XHS runtime assumptions in compose/config/docs with the Docker sidecar topology as the only supported chain.
- [x] 1.2 Refactor XHS status and publish integration code to target the Docker sidecar endpoint and official upstream login semantics.
- [x] 1.3 Remove or demote public host-side and cookie-upload-first surfaces to migration/internal-only status.

## 2. Official skill and QR delivery adaptation

- [x] 2.1 Adapt local XHS login guidance to follow upstream official skill sequencing while preserving AIInSight-specific QR URL/file-path fallback instructions.
- [x] 2.2 Ensure QR-code retrieval persists the artifact and returns operator-usable `qr_image_url`, `qr_image_route`, and/or file-path metadata for non-inline clients.
- [x] 2.3 Update local MCP-facing guidance so OpenCode/Claude Code users are explicitly told how to open the QR when inline rendering is unavailable.

## 3. Verification and end-to-end validation

- [x] 3.1 Add or update tests for Docker-first XHS status behavior, QR URL/file serving, and public contract regressions.
- [x] 3.2 Run targeted verification for compose/runtime wiring, public XHS endpoints, and MCP/public tool guidance.
- [x] 3.3 Perform an end-to-end Docker validation against a real upstream `xhs-mcp` sidecar; if scanning is required, stop and notify the user to scan before continuing.
