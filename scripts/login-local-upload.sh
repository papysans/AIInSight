#!/bin/bash
# ============================================================
# login-local-upload.sh
#
# 在宿主机完成小红书登录，然后将 cookies 注入到 Docker 环境。
#
# 流程:
#   1. 运行 xiaohongshu-login 二进制完成可视浏览器登录
#   2. 读取产出的 cookies.json
#   3. POST 到 AIInsight API 的 /api/xhs/upload-cookies
#   4. 验证登录态
#
# 用法:
#   ./scripts/login-local-upload.sh [--cookies <path>] [--api <url>]
#
# 参数:
#   --cookies <path>  cookies.json 路径（默认自动查找）
#   --api <url>       AIInsight API 地址（默认 http://localhost:8000）
#   --skip-login      跳过登录步骤，直接上传已有 cookies
#   --help            显示帮助
# ============================================================
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
COOKIES_PATH=""
SKIP_LOGIN=false

# ---- 参数解析 ----
while [[ $# -gt 0 ]]; do
    case "$1" in
        --cookies)  COOKIES_PATH="$2"; shift 2 ;;
        --api)      API_URL="$2"; shift 2 ;;
        --skip-login) SKIP_LOGIN=true; shift ;;
        --help|-h)
            sed -n '2,/^# ====/p' "$0" | grep '^#' | sed 's/^# //'
            exit 0
            ;;
        *)  echo "未知参数: $1"; exit 1 ;;
    esac
done

# ---- 架构检测 ----
ARCH=$(uname -m)
OS=$(uname -s)
case "$OS-$ARCH" in
    Darwin-arm64)  SUFFIX="darwin-arm64" ;;
    Darwin-x86_64) SUFFIX="darwin-amd64" ;;
    Linux-x86_64)  SUFFIX="linux-amd64" ;;
    Linux-aarch64) SUFFIX="linux-arm64" ;;
    *)             echo "❌ 不支持的平台: $OS-$ARCH"; exit 1 ;;
esac

# ---- 查找 login 二进制 ----
LOGIN_BIN=""
CANDIDATES=(
    "${XHS_MCP_HOME:-}/xiaohongshu-login-$SUFFIX"
    "./XHS-MCP/xiaohongshu-login-$SUFFIX"
    "../XHS-MCP/xiaohongshu-login-$SUFFIX"
    "../xiaohongshu-mcp/xiaohongshu-login-$SUFFIX"
    "../GlobalInSight/XHS-MCP/xiaohongshu-login-$SUFFIX"
)
for c in "${CANDIDATES[@]}"; do
    if [[ -x "$c" ]]; then
        LOGIN_BIN="$c"
        break
    fi
done

# ---- 查找 cookies 路径 ----
find_cookies() {
    local candidates=(
        "$COOKIES_PATH"
        "runtime/xhs/data/cookies.json"
        "./cookies.json"
        "/tmp/cookies.json"
    )
    for c in "${candidates[@]}"; do
        if [[ -n "$c" && -f "$c" ]]; then
            echo "$c"
            return 0
        fi
    done
    return 1
}

# ---- 步骤 1: 登录 ----
if [[ "$SKIP_LOGIN" != "true" ]]; then
    if [[ -z "$LOGIN_BIN" ]]; then
        echo "❌ 找不到 xiaohongshu-login-$SUFFIX 二进制"
        echo ""
        echo "请将二进制放到以下位置之一:"
        for c in "${CANDIDATES[@]}"; do
            echo "  - $c"
        done
        echo ""
        echo "或设置 XHS_MCP_HOME 环境变量指向包含二进制的目录"
        echo "下载地址: https://github.com/xpzouying/xiaohongshu-mcp/releases"
        exit 1
    fi

    echo "🔑 启动小红书登录..."
    echo "   二进制: $LOGIN_BIN"
    echo ""
    echo "⚠️  请在弹出的浏览器中完成扫码登录"
    echo ""

    # 运行登录工具
    "$LOGIN_BIN"
    echo ""
    echo "✅ 登录流程已完成"
fi

# ---- 步骤 2: 查找 cookies ----
COOKIES_FILE=$(find_cookies) || {
    echo "❌ 找不到 cookies.json 文件"
    echo "搜索路径:"
    echo "  - runtime/xhs/data/cookies.json"
    echo "  - ./cookies.json"
    echo "  - /tmp/cookies.json"
    echo ""
    echo "请用 --cookies <path> 指定路径"
    exit 1
}

echo "📄 使用 cookies: $COOKIES_FILE"

# 检查 web_session
if ! grep -q "web_session" "$COOKIES_FILE"; then
    echo "❌ cookies 文件中未找到 web_session，可能登录未完成"
    exit 1
fi

# ---- 步骤 3: 上传到 Docker 环境 ----
echo "📤 上传 cookies 到 $API_URL/api/xhs/upload-cookies ..."

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$API_URL/api/xhs/upload-cookies" \
    -H "Content-Type: application/json" \
    -d "{\"cookies\": $(cat "$COOKIES_FILE")}" \
    2>&1)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" != "200" ]]; then
    echo "❌ 上传失败 (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi

SUCCESS=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null || echo "False")
MESSAGE=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', ''))" 2>/dev/null || echo "")
VERIFIED=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('login_verified', False))" 2>/dev/null || echo "False")

if [[ "$SUCCESS" == "True" ]]; then
    echo "✅ $MESSAGE"
    if [[ "$VERIFIED" == "True" ]]; then
        echo "🎉 登录验证通过，可以开始发布了！"
    else
        echo "⚠️  Cookies 已写入但登录验证未通过"
        echo "   xhs-mcp 可能需要重启才能加载新 cookies"
        echo "   可运行: docker compose -f docker-compose.xhs.yml restart xhs-mcp"
    fi
else
    echo "❌ 上传失败: $MESSAGE"
    exit 1
fi

# ---- 步骤 4: 最终状态检查 ----
echo ""
echo "📊 最终状态检查..."
STATUS=$(curl -s "$API_URL/api/xhs/status" 2>/dev/null || echo '{}')
MCP_OK=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('mcp_available', False))" 2>/dev/null || echo "False")
LOGIN_OK=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('login_status', False))" 2>/dev/null || echo "False")

echo "  MCP 可用:  $( [[ "$MCP_OK" == "True" ]] && echo '✅' || echo '❌' )"
echo "  登录状态:  $( [[ "$LOGIN_OK" == "True" ]] && echo '✅' || echo '❌' )"
