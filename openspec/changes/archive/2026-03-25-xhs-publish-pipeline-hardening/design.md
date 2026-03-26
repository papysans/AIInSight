## Context

The XHS (Xiaohongshu/小红书) publish pipeline connects three Docker containers: `mcp` (opinion MCP server), `renderer` (card image generator), and `xhs-mcp` (ShunL browser automation sidecar). Real user sessions on 2026-03-25 exposed six technical issues across the login→render→publish chain. Two are P0 blockers that prevent publishing; four degrade reliability.

Current state:
- `_process_image()` only handles `data:image/` URLs; local file paths pass through unchanged and are invisible to `xhs-mcp`
- MCP tool schemas in `server.py` do not expose `account_id`, so AI callers cannot specify which account to use
- `_generate_ascii_qr()` depends on `PIL` and `pyzbar` which are not in `requirements.txt` or the Docker image
- `get_login_qrcode()` line 645 calls `_get_login_qrcode_dir()` without forwarding `account_id`
- Post-publish flow returns `note_url: null` with no fallback resolution

## Goals / Non-Goals

**Goals:**
- P0: Ensure any image path (local, HTTP, data URL) is automatically converted to xhs-mcp-visible shared volume path before publishing
- P0: Expose `account_id` in MCP tool schemas so the full login→check→publish chain uses a consistent account
- P1: Make QR ASCII rendering work in Docker by adding required dependencies
- P1: Fix QR directory isolation so multi-account QR codes don't collide
- P1: Add post-publish note_url recovery with explicit fallback messaging
- Maintain full backward compatibility — all changes are additive/optional

**Non-Goals:**
- Redesigning the multi-container architecture
- Changing the xhs-mcp upstream sidecar itself
- Addressing UX flow issues (#1, #2 from the report) — those are AI skill/prompt layer concerns
- Implementing multi-account UI or account management features

## Decisions

### Decision 1: Expand `_process_image()` to handle local file paths

**Choice**: When `_process_image()` receives a path that doesn't start with `data:image/` or `http`, read the file bytes, write to `XHS_IMAGE_API_DIR`, and return the `XHS_IMAGE_MCP_DIR` equivalent path.

**Why not just require callers to pass data URLs**: The card render client returns local `output_path` values. Forcing every caller to convert defeats the purpose of a normalization layer. The publish pipeline should accept whatever the render pipeline produces.

**Alternative considered**: Mount `outputs/card_previews` into xhs-mcp. Rejected because it exposes unnecessary files to the sidecar and requires Docker config changes.

### Decision 2: Add `account_id` to MCP tool inputSchema, not just Python function signatures

**Choice**: Update `MCP_TOOLS` list in `server.py` to include optional `account_id` property for all 5 XHS tools. The dispatch logic already passes `**arguments` to tool handlers, so no handler changes needed.

**Why**: The Python functions already accept `account_id`, but the MCP protocol only exposes what's in `inputSchema`. AI callers literally cannot pass what's not declared.

### Decision 3: Add PIL/pyzbar as optional dependencies with graceful fallback

**Choice**: Add `Pillow` and `pyzbar` to `requirements.txt`. Add `libzbar0` to Dockerfile `apt-get` line. Keep the existing `try/except ImportError` fallback in `_generate_ascii_qr()`.

**Why**: The fallback already exists and works (returns `None`, QR URL is still provided). Adding the deps just makes the happy path work in Docker.

### Decision 4: Post-publish note_url recovery via best-effort extraction

**Choice**: After successful publish, attempt to extract `note_url` from multiple locations in the response (`data.note_url`, `data.url`, `result.noteId` → construct URL, text content regex). If still null, return explicit message: "已发布成功，但上游未返回 note_url，请在小红书 App 内查看".

**Why not query xhs-mcp for recent posts**: The sidecar doesn't expose a "get my latest post" tool. Adding one is out of scope (non-goal: don't change upstream sidecar).

## Risks / Trade-offs

- **[Risk] Local file read in `_process_image()` could fail if path doesn't exist** → Mitigation: Check `os.path.isfile()` before reading; fall through to original path on any error, preserving current behavior
- **[Risk] `pyzbar` system dependency `libzbar0` adds ~2MB to Docker image** → Acceptable; the ASCII QR is a significant UX improvement
- **[Risk] `account_id` in MCP schema but AI caller doesn't pass it** → No regression; falls back to `get_account_id()` → `"_default"` as today. Strictly additive.
