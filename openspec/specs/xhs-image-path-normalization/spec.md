## ADDED Requirements

### Requirement: Publish pipeline SHALL normalize any image input to xhs-mcp-visible paths
The system SHALL accept image inputs in three formats — local file paths, HTTP/HTTPS URLs, and base64 data URLs — and SHALL automatically convert each to a path readable by the xhs-mcp sidecar container before passing to the upstream publish call.

#### Scenario: Local card preview path is provided for publishing
- **WHEN** `publish_content()` receives an image path like `/app/outputs/card_previews/account/timestamp_card.png`
- **THEN** the system MUST read the file, write it to the shared volume (`XHS_IMAGE_API_DIR`), and pass the corresponding `XHS_IMAGE_MCP_DIR` path to xhs-mcp

#### Scenario: Data URL is provided for publishing
- **WHEN** `publish_content()` receives a `data:image/png;base64,...` string
- **THEN** the system MUST decode the base64 data, write to the shared volume, and pass the xhs-mcp-visible path (existing behavior, preserved)

#### Scenario: HTTP URL is provided for publishing
- **WHEN** `publish_content()` receives an `http://` or `https://` image URL
- **THEN** the system MUST pass the URL through unchanged (xhs-mcp handles remote URLs natively)

#### Scenario: Local file path does not exist
- **WHEN** `_process_image()` receives a local path that does not exist on disk
- **THEN** the system MUST log a warning and return the original path unchanged, preserving current fallback behavior

### Requirement: Image path normalization SHALL not require caller knowledge of container topology
Callers of `publish_xhs_note()` and `publish_content()` SHALL NOT need to know which container serves the image or how volume mounts are configured. The normalization layer MUST handle all path translation transparently.

#### Scenario: MCP tool caller passes render output path directly
- **WHEN** an AI assistant calls `publish_xhs_note` with the `output_path` value returned by `render_cards`
- **THEN** the publish pipeline MUST automatically translate the path without the caller performing any intermediate conversion
