## Why

The user wants AIInSight to stop carrying a split Xiaohongshu story and move fully to the upstream-official `xiaohongshu-mcp` + `xiaohongshu-mcp-skills` model. That migration must be Docker-first from day one, must not rely on a host-side `xhs-mcp` fallback, and must solve the practical QR-display gap for OpenCode/Claude Code clients that cannot reliably render MCP image content inline.

## What Changes

- **BREAKING** Replace the current host-friendly, cookie-centric public XHS integration contract with a Docker-first official-upstream integration contract.
- **BREAKING** Remove host-side `xhs-mcp` from the supported plan and define Docker sidecar/runtime deployment as the primary and only supported chain for this migration.
- Align AIInSight's XHS login workflow with the upstream official tool model: `check_login_status`, `get_login_qrcode`, and `delete_cookies`.
- Add a QR-delivery bridge so official-skill-style login still works when the client cannot display the returned QR image inline; the system must provide a served URL and/or file path that the operator can open manually.
- Update public docs, local skills/prompts, and operator guidance so they follow the official skills flow with AIInSight-specific QR-display adaptation instead of raw cookie-upload guidance.

## Capabilities

### New Capabilities
- `docker-first-official-xhs-runtime`: Defines Docker-first deployment, runtime expectations, and verification behavior for the upstream official XHS MCP integration.
- `xhs-qr-delivery-bridge`: Defines how QR login artifacts are exposed to operators when the client cannot render MCP image payloads inline.

### Modified Capabilities
- `cookie-based-xhs-auth`: Replace the cookie-upload-first public auth contract with an official upstream login contract adapted for Docker-first deployment.
- `mcp-tool-schema-compatibility`: Align public XHS login guidance and exposed tool expectations with the upstream official login tool set and the QR-delivery bridge contract.

## Impact

- Affected code: `docker-compose.xhs.yml`, `app/services/xiaohongshu_publisher.py`, `app/api/endpoints.py`, `opinion_mcp/server.py`, `opinion_mcp/tools/publish.py`, `opinion_mcp/services/backend_client.py`, and XHS helper scripts.
- Affected docs and skills: `README.md`, `docs/XHS_MCP_Architecture.md`, local XHS login/publish guidance, and any local skill/prompt text that currently assumes cookie injection or host-side deployment.
- Affected systems: Docker topology, XHS runtime startup/health checks, login flow, QR distribution, publish preflight validation, and user/operator recovery instructions.
