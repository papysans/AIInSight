#!/bin/bash
# DEPRECATED: This script targeted the old xpzouying/xiaohongshu-mcp sidecar checks.
# Use `docker compose up -d xhs-mcp` and `curl http://localhost:18060/health` instead.

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
AIINSIGHT_XHS_STATUS_URL="${AIINSIGHT_XHS_STATUS_URL:-http://127.0.0.1:8000/api/xhs/status}"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  AIInSight / XHS MCP 健康检查${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

OS_NAME="$(uname -s)"
ARCH="$(uname -m)"

case "$OS_NAME/$ARCH" in
  Darwin/arm64) BIN_SUFFIX="darwin-arm64" ;;
  Darwin/x86_64) BIN_SUFFIX="darwin-amd64" ;;
  Linux/x86_64) BIN_SUFFIX="linux-amd64" ;;
  Linux/amd64) BIN_SUFFIX="linux-amd64" ;;
  *)
    BIN_SUFFIX=""
    ;;
esac

declare -a CANDIDATES=()
if [ -n "${XHS_MCP_HOME:-}" ]; then
  CANDIDATES+=("$XHS_MCP_HOME")
fi

CANDIDATES+=(
  "$REPO_ROOT/XHS-MCP"
  "$REPO_ROOT/../XHS-MCP"
  "$REPO_ROOT/../xiaohongshu-mcp"
  "$REPO_ROOT/../GlobalInSight/XHS-MCP"
)

find_binary_root() {
  if [ -z "$BIN_SUFFIX" ]; then
    return 1
  fi

  local candidate=""
  for candidate in "${CANDIDATES[@]}"; do
    if [ -x "$candidate/xiaohongshu-mcp-$BIN_SUFFIX/xiaohongshu-mcp-$BIN_SUFFIX" ]; then
      printf '%s\n' "$candidate/xiaohongshu-mcp-$BIN_SUFFIX"
      return 0
    fi
    if [ -x "$candidate/xiaohongshu-mcp-$BIN_SUFFIX" ] && [ -x "$candidate/xiaohongshu-login-$BIN_SUFFIX" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

find_source_root() {
  local candidate=""
  for candidate in "${CANDIDATES[@]}"; do
    if [ -f "$candidate/go.mod" ]; then
      printf '%s\n' "$candidate"
      return 0
    fi
  done

  return 1
}

resolve_cookie_file() {
  if [ -n "${COOKIES_PATH:-}" ]; then
    printf '%s\n' "$COOKIES_PATH"
    return 0
  fi

  if [ -f "$REPO_ROOT/runtime/xhs/data/cookies.json" ]; then
    printf '%s\n' "$REPO_ROOT/runtime/xhs/data/cookies.json"
    return 0
  fi

  if [ -f "/tmp/cookies.json" ]; then
    printf '%s\n' "/tmp/cookies.json"
    return 0
  fi

  local binary_root=""
  if binary_root="$(find_binary_root)"; then
    printf '%s\n' "$binary_root/cookies.json"
    return 0
  fi

  local source_root=""
  if source_root="$(find_source_root)"; then
    printf '%s\n' "$source_root/cookies.json"
    return 0
  fi

  printf '%s\n' "$REPO_ROOT/runtime/xhs/data/cookies.json"
}

check_login_via_mcp() {
  local response
  response=$(curl -s -X POST "$XHS_MCP_URL" \
    -H "Content-Type: application/json" \
    -d '[
      {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
          "protocolVersion": "2024-11-05",
          "capabilities": {},
          "clientInfo": {"name": "aiinsight-check", "version": "1.0"}
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
          "name": "check_login_status",
          "arguments": {}
        },
        "id": 2
      }
    ]' 2>/dev/null || true)

  if [ -z "$response" ]; then
    return 1
  fi

  if echo "$response" | grep -q "已登录\|logged in"; then
    printf '%s\n' "$response"
    return 0
  fi

  printf '%s\n' "$response"
  return 2
}

COOKIE_FILE="$(resolve_cookie_file)"

echo "MCP URL: $XHS_MCP_URL"
echo "Cookies 路径: $COOKIE_FILE"
echo ""

echo -e "${BLUE}[1/4] 检查本地 cookies${NC}"
if [ -f "$COOKIE_FILE" ]; then
  size=$(wc -c < "$COOKIE_FILE" | tr -d ' ')
  echo "文件存在，大小: ${size} bytes"
  if grep -q "web_session" "$COOKIE_FILE" 2>/dev/null; then
    echo -e "${GREEN}cookies 包含 web_session ✓${NC}"
  else
    echo -e "${YELLOW}cookies 文件存在，但未检测到 web_session${NC}"
  fi
else
  echo -e "${YELLOW}未找到 cookies 文件${NC}"
fi
echo ""

echo -e "${BLUE}[2/4] 检查 XHS MCP 端口与服务可达性${NC}"
http_code="$(curl -s -o /dev/null -w '%{http_code}' "$XHS_MCP_URL" || true)"
if [ "$http_code" = "200" ] || [ "$http_code" = "405" ]; then
  echo -e "${GREEN}XHS MCP 可访问 ✓${NC} (HTTP ${http_code})"
else
  echo -e "${RED}XHS MCP 不可访问${NC} (HTTP ${http_code:-N/A})"
fi
echo ""

echo -e "${BLUE}[3/4] 检查登录状态${NC}"
set +e
login_response="$(check_login_via_mcp)"
login_status=$?
set -e
if [ "$login_status" -eq 0 ]; then
  echo -e "${GREEN}MCP 返回已登录 ✓${NC}"
elif [ "$login_status" -eq 2 ]; then
  echo -e "${YELLOW}MCP 可访问，但当前未登录或登录状态未确认${NC}"
  echo "如需本地拉起二维码，可运行: ./scripts/open-xhs-login-qrcode.sh"
else
  echo -e "${RED}无法通过 MCP 检查登录状态${NC}"
fi
if [ -n "${login_response:-}" ]; then
  echo "返回摘要:"
  printf '%s\n' "$login_response" | head -n 6
fi
echo ""

echo -e "${BLUE}[4/4] 检查 AIInSight API 侧视角${NC}"
api_status_code="$(curl -s -o /tmp/aiinsight_xhs_status.json -w '%{http_code}' "$AIINSIGHT_XHS_STATUS_URL" || true)"
if [ "$api_status_code" = "200" ]; then
  echo -e "${GREEN}AIInSight API 可访问 ✓${NC}"
  python3 - <<'PY' /tmp/aiinsight_xhs_status.json
import json, sys
path = sys.argv[1]
data = json.load(open(path, "r", encoding="utf-8"))
print(f"mcp_available={data.get('mcp_available')}")
print(f"login_status={data.get('login_status')}")
print(f"message={data.get('message', '')}")
PY
else
  echo -e "${YELLOW}无法从 AIInSight API 获取状态${NC} (HTTP ${api_status_code:-N/A})"
  echo "如果你当前没有启动 api 容器，这一项失败是正常的。"
fi
