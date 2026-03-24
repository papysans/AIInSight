#!/bin/bash
# DEPRECATED: This cloud login helper belongs to the previous xpzouying/cookie-injection workflow.
# Prefer the current Docker sidecar flow via `/api/xhs/login-qrcode`, `/api/xhs/check-login-session/{session_id}`, and `/api/xhs/submit-verification`.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_OUTPUT_DIR="$REPO_ROOT/runtime/xhs/login/cloud"

usage() {
  cat <<'EOF'
用法:
  ./scripts/login-xhs-cloud.sh --url https://xhs.example.com/mcp
  ./scripts/login-xhs-cloud.sh --host xhs.example.com
  ./scripts/login-xhs-cloud.sh https://xhs.example.com

参数:
  --url <url>         远端 XHS MCP 地址，支持带或不带 /mcp
  --host <host>       远端域名或 host:port，默认按 https://<host>/mcp 组装
  --output-dir <dir>  二维码输出目录，默认 runtime/xhs/login/cloud
  --timeout <sec>     二维码请求超时秒数，默认沿用 XHS_QR_TIMEOUT_SECONDS 或 90
  --no-open           只生成二维码文件，不自动打开
  --help              显示帮助

环境变量:
  XHS_MCP_URL         远端 MCP 地址，低优先级，未提供参数时生效
  XHS_QR_OUTPUT_DIR   二维码输出目录
  XHS_QR_NO_OPEN      设为 true 时不自动打开二维码
EOF
}

normalize_url() {
  local value="$1"

  if [[ "$value" =~ ^https?:// ]]; then
    if [[ "$value" == */mcp ]]; then
      printf '%s\n' "$value"
    else
      printf '%s/mcp\n' "${value%/}"
    fi
    return 0
  fi

  printf 'https://%s/mcp\n' "${value%/}"
}

URL_ARG=""
HOST_ARG=""
OUTPUT_DIR="${XHS_QR_OUTPUT_DIR:-$DEFAULT_OUTPUT_DIR}"
NO_OPEN="${XHS_QR_NO_OPEN:-false}"
TIMEOUT_SECONDS="${XHS_QR_TIMEOUT_SECONDS:-90}"

while [ $# -gt 0 ]; do
  case "$1" in
    --url)
      URL_ARG="${2:-}"
      shift 2
      ;;
    --host)
      HOST_ARG="${2:-}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:-}"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:-}"
      shift 2
      ;;
    --no-open)
      NO_OPEN="true"
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      if [ -z "$URL_ARG" ] && [ -z "$HOST_ARG" ]; then
        URL_ARG="$1"
        shift
      else
        echo "未知参数: $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

if [ -n "$URL_ARG" ] && [ -n "$HOST_ARG" ]; then
  echo "不要同时传 --url 和 --host" >&2
  exit 1
fi

REMOTE_TARGET="${URL_ARG:-${HOST_ARG:-${XHS_MCP_URL:-}}}"
if [ -z "$REMOTE_TARGET" ]; then
  echo "缺少远端 XHS MCP 地址" >&2
  usage >&2
  exit 1
fi

REMOTE_URL="$(normalize_url "$REMOTE_TARGET")"

echo "远端 MCP: $REMOTE_URL"
echo "二维码目录: $OUTPUT_DIR"
echo "请求超时: ${TIMEOUT_SECONDS}s"
echo "自动打开: $([ "$NO_OPEN" = "true" ] && echo "否" || echo "是")"
echo ""

XHS_MCP_URL="$REMOTE_URL" \
XHS_QR_OUTPUT_DIR="$OUTPUT_DIR" \
XHS_QR_NO_OPEN="$NO_OPEN" \
XHS_QR_TIMEOUT_SECONDS="$TIMEOUT_SECONDS" \
  "$SCRIPT_DIR/open-xhs-login-qrcode.sh"
