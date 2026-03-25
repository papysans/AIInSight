#!/bin/bash
# DEPRECATED: This script was for building xpzouying/xiaohongshu-mcp ARM64 images.
# The project now uses ShunL12324/xhs-mcp via Dockerfile.xhs-mcp (Node.js + Playwright).
# Use: docker compose build xhs-mcp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DEFAULT_PLATFORM=""
DEFAULT_TAG=""

case "$(uname -m)" in
  arm64|aarch64)
    DEFAULT_PLATFORM="linux/arm64"
    DEFAULT_TAG="aiinsight-xhs-mcp:arm64-patched"
    ;;
  x86_64|amd64)
    DEFAULT_PLATFORM="linux/amd64"
    DEFAULT_TAG="aiinsight-xhs-mcp:amd64-patched"
    ;;
  *)
    DEFAULT_PLATFORM="linux/amd64"
    DEFAULT_TAG="aiinsight-xhs-mcp:patched"
    ;;
esac

XHS_MCP_REF="${XHS_MCP_REF:-main}"
XHS_MCP_REF_KIND="${XHS_MCP_REF_KIND:-heads}"
XHS_MCP_BUILD_PLATFORM="${XHS_MCP_BUILD_PLATFORM:-$DEFAULT_PLATFORM}"
XHS_MCP_LOCAL_IMAGE="${XHS_MCP_LOCAL_IMAGE:-$DEFAULT_TAG}"
XHS_MCP_ARCHIVE_URL="${XHS_MCP_ARCHIVE_URL:-https://github.com/xpzouying/xiaohongshu-mcp/archive/refs/${XHS_MCP_REF_KIND}/${XHS_MCP_REF}.tar.gz}"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  AIInSight / 构建小红书 MCP 修正版镜像${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "源码归档: $XHS_MCP_ARCHIVE_URL"
echo "目标平台: $XHS_MCP_BUILD_PLATFORM"
echo "镜像标签: $XHS_MCP_LOCAL_IMAGE"
echo ""

TMP_DIR="$(mktemp -d /tmp/aiinsight-xhs-src.XXXXXX)"
ARCHIVE_PATH="$TMP_DIR/xhs-mcp.tar.gz"
SRC_DIR="$TMP_DIR/src"
mkdir -p "$SRC_DIR"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

curl -L --fail --retry 2 --retry-delay 1 "$XHS_MCP_ARCHIVE_URL" -o "$ARCHIVE_PATH"
tar -xzf "$ARCHIVE_PATH" -C "$SRC_DIR" --strip-components=1

docker build \
  --platform "$XHS_MCP_BUILD_PLATFORM" \
  -t "$XHS_MCP_LOCAL_IMAGE" \
  -f- \
  "$SRC_DIR" <<'EOF'
ARG TARGETARCH

FROM --platform=$BUILDPLATFORM golang:1.24 AS builder
ARG TARGETARCH
WORKDIR /src
ENV GOPROXY=https://goproxy.cn,direct
ENV GOSUMDB=sum.golang.google.cn
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=$TARGETARCH go build -ldflags="-s -w" -o /out/app .

FROM debian:bookworm-slim
ENV TZ=Asia/Shanghai
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    ca-certificates \
    fonts-liberation \
    fonts-noto-cjk \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libnss3 \
    libxshmfence1 \
    tzdata \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /out/app ./app
RUN mkdir -p /app/data /app/images && chmod 777 /app/images
ENV ROD_BROWSER_BIN=/usr/bin/chromium
EXPOSE 18060
CMD ["./app"]
EOF

echo ""
echo -e "${GREEN}镜像构建完成${NC}"
echo ""
echo "如需让 AIInSight sidecar 使用这个镜像："
echo "XHS_MCP_IMAGE=$XHS_MCP_LOCAL_IMAGE XHS_MCP_PLATFORM=$XHS_MCP_BUILD_PLATFORM docker compose -f $REPO_ROOT/docker-compose.yml -f $REPO_ROOT/docker-compose.xhs.yml up -d --force-recreate xhs-mcp api mcp"
echo ""
echo -e "${YELLOW}说明:${NC}"
echo "- 这个脚本直接使用上游源码构建，但改用 Debian + Chromium，绕开上游 ARM64 镜像里浏览器自动下载失败的问题。"
echo "- 默认拉取 main 分支；如果要固定版本，可设置 XHS_MCP_REF_KIND=tags 与 XHS_MCP_REF=<tag>。"
