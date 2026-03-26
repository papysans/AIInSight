## 1. Image Path Normalization (P0)

- [x] 1.1 Expand `_process_image()` in `opinion_mcp/services/xiaohongshu_publisher.py` to detect local file paths (not starting with `data:` or `http`), read file bytes, write to `XHS_IMAGE_API_DIR`, and return `XHS_IMAGE_MCP_DIR` equivalent path
- [x] 1.2 Add `os.path.isfile()` guard before reading; log warning and return original path on failure
- [x] 1.3 Apply same fix to `app/services/xiaohongshu_publisher.py` (legacy copy)
- [x] 1.4 Add unit test: `_process_image("/app/outputs/card_previews/test.png")` with mocked env vars returns `/app/images/test.png`
- [x] 1.5 Add unit test: `_process_image("/nonexistent/path.png")` returns original path unchanged

## 2. MCP Tool Schema account_id Exposure (P0)

- [x] 2.1 Add `"account_id": {"type": "string", "description": "账号 ID（可选，用于多账号场景）"}` to `publish_xhs_note` inputSchema properties in `opinion_mcp/server.py`
- [x] 2.2 Add same `account_id` property to `check_xhs_status` inputSchema
- [x] 2.3 Add same `account_id` property to `get_xhs_login_qrcode` inputSchema
- [x] 2.4 Add same `account_id` property to `check_xhs_login_session` inputSchema
- [x] 2.5 Add same `account_id` property to `submit_xhs_verification` inputSchema
- [x] 2.6 Verify dispatch in `_handle_tool_call()` passes `account_id` from `arguments` to tool handlers (should work via `**arguments` spread, confirm)

## 3. QR Code Dependencies (P1)

- [x] 3.1 Add `Pillow>=10.0.0` and `pyzbar>=0.1.9` to `requirements.txt`
- [x] 3.2 Add `libzbar0` to `apt-get install` line in `Dockerfile`
- [x] 3.3 Verify `tests/test_ascii_qr.py` passes with new dependencies installed

## 4. QR Code Directory Account Isolation Fix (P1)

- [x] 4.1 Fix `get_login_qrcode()` line 645: change `self._get_login_qrcode_dir()` to `self._get_login_qrcode_dir(account_id)` to pass account_id through
- [x] 4.2 Apply same fix in `app/services/xiaohongshu_publisher.py` (legacy copy)
- [x] 4.3 Add unit test: verify QR file path includes account_id subdirectory when account_id is provided

## 5. Post-Publish note_url Recovery (P1)

- [x] 5.1 In `opinion_mcp/services/xiaohongshu_publisher.py` `publish_content()`, after successful MCP call, extract `noteId` from nested result and construct `note_url` as `https://www.xiaohongshu.com/explore/{noteId}` when `note_url`/`url` fields are absent
- [x] 5.2 In `opinion_mcp/tools/publish.py` `publish_xhs_note()`, expand note_url extraction to check `data.noteId` in addition to `data.note_url` and `data.url`
- [x] 5.3 When note_url is still null after all extraction attempts, set `message` to "已发布成功，但上游未返回 note_url，请在小红书 App 内查看"
- [x] 5.4 Apply same extraction logic in `app/services/xiaohongshu_publisher.py` (legacy copy)
- [x] 5.5 Add unit test for noteId-to-URL construction

## 6. Verification

- [x] 6.1 Run full test suite: `pytest tests/`
- [x] 6.2 Build Docker images: `docker compose build mcp`
- [x] 6.3 Verify MCP tool list includes `account_id` in all XHS tool schemas via `/mcp/tools` endpoint
