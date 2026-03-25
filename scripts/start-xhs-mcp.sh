#!/bin/bash
# DEPRECATED: This script was for starting xpzouying/xiaohongshu-mcp locally.
# Use: docker compose up -d xhs-mcp

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
XHS_MCP_PORT="${XHS_MCP_PORT:-18060}"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  AIInSight / 小红书 MCP 启动器${NC}"
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

MODE=""
XHS_DIR=""
XHS_RUN_CMD=()
XHS_LOGIN_CMD=()
COOKIE_FILE=""

if BINARY_ROOT="$(find_binary_root)"; then
  MODE="binary"
  XHS_DIR="$BINARY_ROOT"
  XHS_RUN_CMD=("./xiaohongshu-mcp-$BIN_SUFFIX")
  XHS_LOGIN_CMD=("./xiaohongshu-login-$BIN_SUFFIX")
  COOKIE_FILE="$XHS_DIR/cookies.json"
elif SOURCE_ROOT="$(find_source_root)"; then
  if ! command -v go >/dev/null 2>&1; then
    echo -e "${RED}错误: 找到了 xiaohongshu-mcp 源码，但当前机器没有 Go${NC}"
    echo "请安装 Go，或设置 XHS_MCP_HOME 指向已经构建好的二进制目录。"
    exit 1
  fi
  MODE="source"
  XHS_DIR="$SOURCE_ROOT"
  XHS_RUN_CMD=("go" "run" ".")
  XHS_LOGIN_CMD=("go" "run" "cmd/login/main.go")
  if [ -n "${COOKIES_PATH:-}" ]; then
    COOKIE_FILE="$COOKIES_PATH"
  elif [ -f "/tmp/cookies.json" ]; then
    COOKIE_FILE="/tmp/cookies.json"
  else
    COOKIE_FILE="$XHS_DIR/cookies.json"
  fi
else
  echo -e "${RED}错误: 未找到可用的 xiaohongshu-mcp 安装${NC}"
  echo ""
  echo "可选做法："
  echo "1. 设置 XHS_MCP_HOME 指向已下载的二进制目录或源码目录"
  echo "2. 将仓库克隆到以下任一位置："
  for candidate in "${CANDIDATES[@]}"; do
    echo "   - $candidate"
  done
  echo ""
  echo "上游仓库: https://github.com/xpzouying/xiaohongshu-mcp"
  exit 1
fi

check_login_via_mcp() {
  local response
  response=$(curl -s -X POST "http://127.0.0.1:${XHS_MCP_PORT}/mcp" \
    -H "Content-Type: application/json" \
    -d '[
      {
        "jsonrpc": "2.0",
        "method": "initialize",
        "params": {
          "protocolVersion": "2024-11-05",
          "capabilities": {},
          "clientInfo": {"name": "startup-check", "version": "1.0"}
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

  if echo "$response" | grep -q "已登录\|logged in"; then
    return 0
  fi
  return 1
}

check_login_by_cookie() {
  if [ ! -f "$COOKIE_FILE" ] || [ ! -s "$COOKIE_FILE" ]; then
    return 1
  fi

  if grep -q "web_session" "$COOKIE_FILE" 2>/dev/null; then
    return 0
  fi

  return 1
}

do_login() {
  echo -e "${BLUE}启动登录工具...${NC}"
  echo "请在弹出的浏览器窗口中完成登录。"
  echo ""
  (
    cd "$XHS_DIR"
    "${XHS_LOGIN_CMD[@]}"
  )
}

echo -e "${BLUE}运行模式: ${MODE}${NC}"
echo "安装目录: $XHS_DIR"
echo "Cookie 文件: $COOKIE_FILE"
echo ""

if [ "${XHS_MCP_DRY_RUN:-false}" = "true" ]; then
  echo -e "${YELLOW}Dry run 模式：仅检查配置，不启动服务${NC}"
  echo "启动命令: ${XHS_RUN_CMD[*]}"
  echo "登录命令: ${XHS_LOGIN_CMD[*]}"
  exit 0
fi

if curl -s "http://127.0.0.1:${XHS_MCP_PORT}/mcp" >/dev/null 2>&1; then
  echo -e "${GREEN}检测到 XHS MCP 已经在运行: http://127.0.0.1:${XHS_MCP_PORT}/mcp${NC}"
  if check_login_via_mcp; then
    echo -e "${GREEN}当前服务登录状态有效 ✓${NC}"
  else
    echo -e "${YELLOW}当前服务可访问，但登录状态未确认${NC}"
  fi
  echo "AIInSight 当前会继续通过 host.docker.internal:${XHS_MCP_PORT}/mcp 调用它。"
  exit 0
fi

echo -e "${BLUE}检查登录状态...${NC}"
if check_login_by_cookie; then
  echo -e "${GREEN}检测到本地 cookies，可直接尝试启动服务 ✓${NC}"
else
  echo -e "${YELLOW}未检测到有效登录状态${NC}"
  echo "首次使用建议先登录，否则发布会失败。"
  echo ""
  read -r -p "是否现在执行登录？(y/n) " REPLY
  if [[ "$REPLY" =~ ^[Yy]$ ]]; then
    if ! do_login; then
      echo -e "${RED}登录失败或已取消${NC}"
      exit 1
    fi
  else
    echo -e "${YELLOW}跳过登录，服务会启动，但发布功能可能不可用${NC}"
  fi
fi

if [ "${XHS_MCP_HEADLESS:-true}" = "false" ]; then
  XHS_RUN_CMD+=("-headless=false")
fi

echo ""
echo -e "${GREEN}启动小红书 MCP 服务...${NC}"
echo "地址: http://127.0.0.1:${XHS_MCP_PORT}/mcp"
echo "AIInSight 容器访问地址: http://host.docker.internal:${XHS_MCP_PORT}/mcp"
echo "提示: 按 Ctrl+C 停止服务"
echo ""

(
  cd "$XHS_DIR"
  "${XHS_RUN_CMD[@]}"
)
