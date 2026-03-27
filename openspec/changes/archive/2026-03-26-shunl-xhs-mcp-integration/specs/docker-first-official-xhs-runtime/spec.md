## MODIFIED Requirements

### Requirement: XHS MCP Docker 镜像

Docker sidecar 从 `xpzouying/xiaohongshu-mcp` (Go + Chrome) 切换为基于 `@sillyl12324/xhs-mcp` (Node.js + Playwright + Chromium) 的自建镜像。

镜像 SHALL 包含：
- Node.js 20 LTS
- Playwright Chromium 浏览器
- `@sillyl12324/xhs-mcp` npm 包

#### Scenario: 构建 Docker 镜像

- **WHEN** 执行 `docker build -f Dockerfile.xhs-mcp .`
- **THEN** 生成包含 Node.js + Playwright + Chromium 的镜像，能以 HTTP 模式在 18060 端口提供 MCP 服务

#### Scenario: Apple Silicon 兼容

- **WHEN** 在 Apple Silicon (arm64) 机器上构建和运行
- **THEN** 镜像使用 `linux/arm64` 平台，Playwright Chromium 正常安装和运行

### Requirement: Docker Compose 配置

`docker-compose.yml` 和 `docker-compose.xhs.yml` 中的 xhs-mcp 服务 SHALL 更新为新镜像配置。

环境变量映射：
- `XHS_MCP_HEADLESS=true`
- `XHS_MCP_DATA_DIR=/data`
- `XHS_MCP_REQUEST_INTERVAL=2000`

Volume 挂载：
- `./runtime/xhs/data:/data`（SQLite 数据库 + 会话持久化）
- `./runtime/xhs/images:/app/images`（发布图片）

#### Scenario: Docker Compose 启动

- **WHEN** 执行 `docker compose up -d xhs-mcp`
- **THEN** 容器正常启动，`http://xhs-mcp:18060/mcp` 可访问，headless 模式运行

#### Scenario: Volume 持久化

- **WHEN** xhs-mcp 容器被销毁并重建
- **THEN** SQLite 数据库通过 volume 挂载保留，已登录的会话不丢失
