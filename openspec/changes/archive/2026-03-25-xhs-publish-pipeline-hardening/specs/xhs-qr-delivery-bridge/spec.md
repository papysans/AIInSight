## MODIFIED Requirements

### Requirement: QR login responses SHALL provide a non-inline access path for operators
When the system obtains an XHS login QR code from the upstream official login tool flow, it SHALL make that QR artifact available through at least one operator-accessible non-inline path such as a served URL or file path. QR code files SHALL be stored in account-isolated directories when `account_id` is provided.

#### Scenario: Client cannot render MCP QR image inline
- **WHEN** an operator uses a client that does not display the returned QR image content directly
- **THEN** the system MUST return enough metadata for the operator to open the QR manually, including a served URL and/or local file path

#### Scenario: QR code is generated with explicit account_id
- **WHEN** `get_login_qrcode(account_id="user123")` is called
- **THEN** the QR image file MUST be stored under `outputs/xhs_login/user123/` and the returned `qr_image_path` MUST reflect the account-specific directory

#### Scenario: QR code is generated without account_id
- **WHEN** `get_login_qrcode()` is called without an `account_id`
- **THEN** the QR image file MUST be stored under the base `outputs/xhs_login/` directory (backward compatible)

## ADDED Requirements

### Requirement: QR ASCII rendering dependencies SHALL be available in the Docker runtime
The Docker image MUST include all dependencies required for `_generate_ascii_qr()` to function, specifically `Pillow` and `pyzbar` Python packages and the `libzbar0` system library.

#### Scenario: ASCII QR code generation in Docker container
- **WHEN** `_generate_ascii_qr()` is called with valid QR PNG bytes inside the Docker `mcp` container
- **THEN** the function MUST successfully return ASCII art representation of the QR code without `ImportError`

#### Scenario: ASCII QR dependency is unavailable (non-Docker local dev)
- **WHEN** `_generate_ascii_qr()` is called in an environment where PIL or pyzbar is not installed
- **THEN** the function MUST return `None` and log a warning, without raising an exception (existing graceful fallback preserved)
