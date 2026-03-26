## Why

XHS publish pipeline has 6 confirmed technical issues surfaced during real user publishing sessions (2026-03-25). Two are P0 blockers (account mismatch causing `Account not found: _default`, cross-container image path invisibility causing `No valid image files found`). The remaining four degrade reliability and trust: missing QR ASCII dependencies, QR directory not account-isolated, login status inconsistency, and missing `note_url` in publish results.

## What Changes

- **MCP tool schema exposes `account_id`**: All XHS-related MCP tools (`publish_xhs_note`, `check_xhs_status`, `get_xhs_login_qrcode`, `check_xhs_login_session`, `submit_xhs_verification`) add optional `account_id` parameter to their `inputSchema`
- **Image path auto-conversion to shared volume**: `_process_image()` handles local file paths (e.g., `outputs/card_previews/...`) by reading, base64-encoding, and writing to the shared volume — not just `data:image/` URLs
- **QR code ASCII rendering dependencies**: Add `Pillow` and `pyzbar` to `requirements.txt` and Dockerfile
- **QR code directory account isolation fix**: Pass `account_id` through `get_login_qrcode()` to `_get_login_qrcode_dir()` call at line 645
- **Post-publish note URL resolution**: Add fallback `note_url` recovery after successful publish, with clear messaging when unavailable
- **Publish result messaging**: When `note_url` is null, return explicit user-facing message instead of silent null

## Capabilities

### New Capabilities
- `xhs-image-path-normalization`: Automatic cross-container image path translation in the publish pipeline — `_process_image()` accepts local paths, HTTP URLs, and data URLs, always outputting xhs-mcp-visible shared volume paths

### Modified Capabilities
- `mcp-tool-schema-compatibility`: MCP tool definitions add optional `account_id` parameter to all XHS tools
- `xhs-publish-result-normalization`: Post-publish note_url recovery step and explicit fallback messaging
- `xhs-qr-delivery-bridge`: QR directory isolation fix and ASCII rendering dependency resolution

## Impact

- **Code**: `opinion_mcp/server.py` (tool schemas), `opinion_mcp/services/xiaohongshu_publisher.py` (`_process_image`, `get_login_qrcode`, `publish_content`), `opinion_mcp/tools/publish.py` (result handling)
- **Dependencies**: `requirements.txt` adds `Pillow`, `pyzbar`; `Dockerfile` adds `libzbar0` system package
- **Docker**: No volume mapping changes needed — existing `./runtime/xhs/images` mapping is sufficient
- **API**: No breaking changes — `account_id` is optional everywhere
