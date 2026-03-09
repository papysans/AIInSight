#!/bin/bash

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
XHS_MCP_PORT="${XHS_MCP_PORT:-18060}"
XHS_MCP_URL="${XHS_MCP_URL:-http://127.0.0.1:${XHS_MCP_PORT}/mcp}"
XHS_QR_OUTPUT_DIR="${XHS_QR_OUTPUT_DIR:-$REPO_ROOT/runtime/xhs/login}"
XHS_QR_NO_OPEN="${XHS_QR_NO_OPEN:-false}"
XHS_QR_TIMEOUT_SECONDS="${XHS_QR_TIMEOUT_SECONDS:-${XHS_LOGIN_QRCODE_TIMEOUT_SECONDS:-30}}"

mkdir -p "$XHS_QR_OUTPUT_DIR"

TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
RAW_RESPONSE_FILE="$(mktemp)"
META_FILE="$(mktemp)"
QR_OUTPUT_FILE="$XHS_QR_OUTPUT_DIR/xhs-login-qrcode-${TIMESTAMP}.png"

cleanup() {
  rm -f "$RAW_RESPONSE_FILE" "$META_FILE"
}
trap cleanup EXIT

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  AIInSight / 小红书登录二维码${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "MCP URL: $XHS_MCP_URL"
echo "输出目录: $XHS_QR_OUTPUT_DIR"
echo ""

http_code="$(curl -s -o /dev/null -w '%{http_code}' "$XHS_MCP_URL" || true)"
if [ "$http_code" != "200" ] && [ "$http_code" != "405" ]; then
  echo -e "${RED}XHS MCP 当前不可访问${NC} (HTTP ${http_code:-N/A})"
  echo "请先启动："
  echo "  docker compose -f docker-compose.yml -f docker-compose.xhs.yml up -d"
  echo "或运行："
  echo "  ./scripts/start-xhs-mcp.sh"
  echo ""
  echo "如果你在调用云端服务，请先设置："
  echo "  export XHS_MCP_URL=https://<your-host>/mcp"
  exit 1
fi

curl -s --connect-timeout 5 --max-time "$XHS_QR_TIMEOUT_SECONDS" -X POST "$XHS_MCP_URL" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "jsonrpc": "2.0",
      "method": "initialize",
      "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "aiinsight-login", "version": "1.0"}
      },
      "id": 1
    },
    {
      "jsonrpc": "2.0",
      "method": "notifications/initialized",
      "params": {}
    },
    {
      "jsonrpc": "2.0",
      "method": "tools/call",
      "params": {
        "name": "get_login_qrcode",
        "arguments": {}
      },
      "id": 2
    }
  ]' > "$RAW_RESPONSE_FILE"

if [ ! -s "$RAW_RESPONSE_FILE" ]; then
  echo -e "${RED}二维码请求失败或超时${NC}"
  echo "请确认 XHS MCP 服务可达，并可适当增大 XHS_QR_TIMEOUT_SECONDS。"
  exit 1
fi

python3 - <<'PY' "$RAW_RESPONSE_FILE" "$QR_OUTPUT_FILE" "$META_FILE"
import base64
import json
import sys
from pathlib import Path

raw_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
meta_path = Path(sys.argv[3])

try:
    payload = json.loads(raw_path.read_text(encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: 无法解析 MCP 响应: {exc}")
    sys.exit(1)

if not isinstance(payload, list):
    print("ERROR: MCP 返回格式异常，预期为 JSON 数组")
    sys.exit(1)

tool_result = next((item for item in payload if item.get("id") == 2), None)
if not tool_result:
    print("ERROR: MCP 响应中未找到 get_login_qrcode 返回值")
    sys.exit(1)

if "error" in tool_result:
    err = tool_result["error"]
    print(f"ERROR: {err.get('message', err)}")
    sys.exit(1)

content = (tool_result.get("result") or {}).get("content") or []
message = ""
image_b64 = None

for part in content:
    if part.get("type") == "text" and not message:
        message = part.get("text", "")
    if part.get("type") == "image" and part.get("mimeType") == "image/png":
        image_b64 = part.get("data")

if not image_b64:
    print("ERROR: 响应中未找到二维码图片数据")
    if message:
        print(message)
    sys.exit(1)

output_path.write_bytes(base64.b64decode(image_b64))
meta_path.write_text(
    json.dumps(
        {
            "message": message.strip(),
            "qr_file": str(output_path),
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)
PY

message="$(python3 - <<'PY' "$META_FILE"
import json
import sys

meta = json.load(open(sys.argv[1], "r", encoding="utf-8"))
print(meta.get("message", ""))
PY
)"

echo ""
echo -e "${GREEN}二维码已生成 ✓${NC}"
if [ -n "$message" ]; then
  printf '%s\n' "$message"
fi
echo "文件: $QR_OUTPUT_FILE"

if [ "$XHS_QR_NO_OPEN" = "true" ]; then
  echo -e "${YELLOW}已跳过自动打开${NC} (XHS_QR_NO_OPEN=true)"
  exit 0
fi

OS_NAME="$(uname -s)"
if [ "$OS_NAME" = "Darwin" ] && command -v open >/dev/null 2>&1; then
  open "$QR_OUTPUT_FILE"
  echo "已使用 macOS Preview 打开二维码。"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$QR_OUTPUT_FILE" >/dev/null 2>&1 &
  echo "已使用 xdg-open 打开二维码。"
else
  echo -e "${YELLOW}当前系统没有可用的自动打开命令，请手动打开该图片扫码。${NC}"
fi
