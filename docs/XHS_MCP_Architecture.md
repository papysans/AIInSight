# 小红书 MCP (xhs-mcp) 架构分析与集成指南

> 基于 [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp) 源码深度分析。

---

## 目录

1. [核心架构](#核心架构)
2. [登录流程分析](#登录流程分析)
3. [Cookies 机制](#cookies-机制)
4. [已知问题与坑](#已知问题与坑)
5. [AIInSight 集成现状](#aiinsight-集成现状)
6. [云部署方案评估](#云部署方案评估)
7. [本地登录脚本](#本地登录脚本)

---

## 核心架构

### xhs-mcp 工作原理

xhs-mcp 是一个 Go + go-rod (headless Chromium) 的 MCP server，**所有操作都通过无头浏览器完成**：

```
MCP Client → HTTP POST /mcp (JSON-RPC) → xhs-mcp → go-rod headless browser → xiaohongshu.com
```

### 关键设计：无状态浏览器

**每次工具调用都会创建一个全新的浏览器实例**：

```go
// service.go - 所有操作的入口
func (s *XiaohongshuService) CheckLoginStatus(ctx context.Context) {
    b := newBrowser()    // 每次都 new
    defer b.Close()      // 用完就关
    page := b.NewPage()
    // ...
}
```

`newBrowser()` → `browser.NewBrowser()` → `headless_browser.New()` 流程：

1. 读取 cookies 文件（通过 `COOKIES_PATH` 环境变量指定路径）
2. 启动新的 Chromium 实例（使用 go-rod/stealth 反检测）
3. 通过 CDP `Network.setCookies` 注入 cookies
4. 返回浏览器实例

**影响**：每次 API 调用都要启动/关闭 Chromium，导致响应慢（1.5~5 秒）。

### 提供的 13 个 MCP 工具

| 工具 | 说明 | 需要登录 |
|------|------|----------|
| `check_login_status` | 检查登录状态 | 否（去 XHS 检查） |
| `get_login_qrcode` | 获取登录二维码 | 否 |
| `search_feeds` | 搜索笔记 | 是 |
| `get_feeds_list` | 获取推荐 Feed | 是 |
| `get_feed_detail` | 获取笔记详情 | 是 |
| `publish_content` | 发布图文笔记 | 是 |
| `publish_video` | 发布视频笔记 | 是 |
| `get_user_profile` | 获取用户主页 | 是 |
| `comment_feed` | 评论笔记 | 是 |
| `like_feed` | 点赞笔记 | 是 |
| `favorite_feed` | 收藏笔记 | 是 |
| `delete_cookies` | 删除 cookies | 否 |
| `get_comment_feed_list` | 获取评论列表 | 是 |

---

## 登录流程分析

### check_login_status

```go
// xiaohongshu/login.go
func (a *LoginAction) CheckLoginStatus(ctx context.Context) (bool, error) {
    pp.MustNavigate("https://www.xiaohongshu.com/explore").MustWaitLoad()
    time.Sleep(1 * time.Second)
    exists, _, err := pp.Has(`.main-container .user .link-wrapper .channel`)
    return exists, err
}
```

**判断逻辑**：导航到 XHS explore 页面，检查侧边栏「我」按钮是否存在。
- 已登录 → 该元素存在 → 返回 `true`
- 未登录 → 页面显示登录弹窗 → 元素不存在 → 返回 `false`

### get_login_qrcode

```go
// xiaohongshu/login.go
func (a *LoginAction) FetchQrcodeImage(ctx context.Context) (string, bool, error) {
    pp.MustNavigate("https://www.xiaohongshu.com/explore").MustWaitLoad()
    time.Sleep(2 * time.Second)
    // 先检查是否已登录
    if exists, _, _ := pp.Has(".main-container .user .link-wrapper .channel"); exists {
        return "", true, nil  // 已登录，无需扫码
    }
    // 未登录，获取二维码
    src, err := pp.MustElement(".login-container .qrcode-img").Attribute("src")
    return *src, false, nil
}
```

**扫码后**：后台 goroutine 每 500ms 轮询检查登录元素，成功后保存 cookies。

```go
// service.go
go func() {
    if loginAction.WaitForLogin(ctxTimeout) {
        saveCookies(page)  // 从浏览器提取 cookies 写入文件
    }
}()
```

---

## Cookies 机制

### 文件路径解析 (`cookies/cookies.go`)

```go
func GetCookiesFilePath() string {
    // 1. 优先检查旧路径 /tmp/cookies.json（向后兼容）
    if _, err := os.Stat("/tmp/cookies.json"); err == nil {
        return "/tmp/cookies.json"
    }
    // 2. 使用环境变量 COOKIES_PATH
    path := os.Getenv("COOKIES_PATH")
    if path == "" {
        path = "cookies.json"  // fallback 当前目录
    }
    return path
}
```

**AIInSight 配置**：`COOKIES_PATH=/app/data/cookies.json`

### Cookies 格式

xhs-mcp 使用 `go-rod/rod/lib/proto.NetworkCookie` 的 JSON 序列化格式：

```json
[
  {
    "name": "web_session",
    "value": "040069b386574f2b...",
    "domain": ".xiaohongshu.com",
    "path": "/",
    "expires": 1804576159.678,
    "size": 49,
    "httpOnly": true,
    "secure": true,
    "session": false,
    "sameSite": "",
    "priority": "Medium",
    "sameParty": false,
    "sourceScheme": "Secure",
    "sourcePort": 443
  }
]
```

**关键字段**：
- JSON tag 全部小写 camelCase（`httpOnly` 而非 `HttpOnly`）
- `expires` 是 Unix 时间戳（浮点数），`-1` 表示 session cookie
- `web_session` 是判断登录态的核心 cookie

### 加载流程

```
headless_browser.New()
  → json.Unmarshal(cookiesJSON, &[]*proto.NetworkCookie)
  → proto.CookiesToParams(cookies)  // NetworkCookie → NetworkCookieParam
  → browser.MustSetCookies(cookies...)  // CDP Network.setCookies
```

---

## 已知问题与坑

### 1. Docker Headless 浏览器登录无效

**现象**：在 Docker 容器中通过 headless 浏览器（Playwright 或 go-rod）打开 XHS 登录页，即使成功获取二维码并扫码，得到的 `web_session` cookie 也是无效的。

**原因**：小红书后端检测到 headless 浏览器特征（即使使用了 stealth mode），将该 session 标记为无效。表现为：
- Cookie 文件中 `web_session` 存在但 value 无法通过 XHS 后端验证
- `check_login_status` 打开 explore 页面后被重定向到登录页
- `search_feeds` 超时返回 HTTP 204 (No Content)

**解决方案**：使用本地 headed（有 GUI 的）真实浏览器登录，导出 cookies 后注入。

### 2. `WaitForLogin` 在 Docker 中不可靠

**现象**：go-rod 的 `WaitForLogin` goroutine 在 Docker headless 环境中经常无法检测到登录跳转。

**原因**：
- 轮询 ``.main-container .user .link-wrapper .channel`` 元素，但 headless 模式下页面可能不会正常跳转
- XHS 的反爬策略可能阻止了 headless 浏览器的页面更新

### 3. 每次调用都启动新浏览器

**影响**：
- 每个 MCP tool 调用需要 1.5~5 秒（冷启动 Chromium）
- `search_feeds` 等操作可能需要 20~60 秒
- 高峰期 Chromium 进程可能堆积

### 4. go-rod UserAgent 写死

```go
// headless_browser v0.3.0
UserAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
```

UA 写死为 Chrome 124 macOS，但容器内运行的是 Linux Chromium 145。如果 XHS 做 UA-环境一致性检测，这也是一个被识别的信号。

### 5. ARM64 需要特殊镜像

上游 Dockerfile 构建 `GOARCH=amd64` 并安装 `google-chrome-stable`（仅 amd64）。在 ARM64 Mac 上必须使用自定义镜像：
- 镜像：`aiinsight-xhs-mcp:arm64-patched`
- 浏览器：`/usr/bin/chromium`（Debian ARM64 版）
- 环境变量：`ROD_BROWSER_BIN=/usr/bin/chromium`

---

## AIInSight 集成现状

### 架构

```
┌─────────────────────────────────┐
│ MCP Client (Copilot/Opencode)   │
│                                 │
│  skills: ai-insight,            │
│          ai-topic-analyzer      │
└───────────┬─────────────────────┘
            │ MCP (stdio/sse)
┌───────────▼─────────────────────┐
│ opinion_mcp (MCP Server)        │
│  public tools:                  │
│    check_xhs_status             │
│    upload_xhs_cookies           │
│    publish_to_xhs               │
└───────────┬─────────────────────┘
            │ HTTP
┌───────────▼─────────────────────┐
│ FastAPI (api)                   │
│  /api/xhs/status                │  ←  检查登录
│  /api/xhs/upload-cookies         │  ←  Cookie 注入
│  /api/xhs/publish                │  ←  发布内容
└───────┬───────────┬─────────────┘
        │           │
   ┌────▼────┐ ┌────▼─────────────┐
   │renderer │ │ xhs-mcp (go-rod) │
   │Playwright│ │ headless Chrome  │
   └─────────┘ └──────────────────┘
```

### Docker Compose

- `docker-compose.yml` — 基础服务 (api, mcp, renderer)
- `docker-compose.xhs.yml` — 叠加 xhs-mcp 及相关配置

共享卷：`./runtime/xhs/data` → api(`/app/runtime/xhs/data`) + xhs-mcp(`/app/data`)

### 公开登录路径

| 路径 | 端点 / 工具 | 说明 |
|------|-------------|------|
| **状态检查** | `GET /api/xhs/status` / `check_xhs_status` | 检查 sidecar 可用性和当前登录状态 |
| **获取二维码** | `GET /api/xhs/login-qrcode` / `get_xhs_login_qrcode` | 获取官方登录二维码，并返回 URL / route / file-path 供客户端打开 |
| **重置登录** | `POST /api/xhs/login/reset` / `reset_xhs_login` | 调用上游 `delete_cookies` 清除登录状态，重新扫码 |

> 说明：对于 OpenCode / Claude Code 等无法稳定渲染 MCP 图片内容的客户端，AIInSight 会把二维码持久化为 PNG，并返回 `qr_image_url`、`qr_image_route`、`qr_image_path` 作为桥接交付方式。

---

## 云部署方案评估

### 问题本质

小红书检测 headless 浏览器并使登录 session 无效化。这意味着所有「服务器端 headless 浏览器 → 生成 QR 码 → 扫码登录」的流程都可能产生**无效 cookies**。

### 当前结论

当前支持的公开方案以 **Docker sidecar + 官方 QR 登录** 为主。

#### 方案：Docker sidecar + 官方登录工具 + 二维码桥接

```
Docker: api / mcp / renderer / xhs-mcp
登录: check_xhs_status → get_xhs_login_qrcode → 用户扫码 → check_xhs_status
桥接: 返回 qr_image_url / qr_image_route / qr_image_path 供用户打开二维码
```

- **优点**：与 upstream 官方 `xiaohongshu-mcp` / `xiaohongshu-mcp-skills` 语义一致
- **缺点**：仍受上游 Docker/headless 稳定性约束，平台兼容性需要实测
- **可行性**：✅ 作为当前支持主链路推进；真实扫码验证需在实现完成后继续确认

---

## 历史兼容 / 内部排障说明

仓库中仍保留的 cookie 注入脚本、本地登录脚本、Playwright 登录代理等能力，应视为历史兼容或内部排障材料，不属于当前支持的公开登录合同。

---

## 附录：xhs-mcp 源码关键文件

| 文件 | 作用 |
|------|------|
| `main.go` | 入口，解析参数（headless, bin, port） |
| `service.go` | 业务逻辑，所有 MCP tool 的实现 |
| `mcp_handlers.go` | MCP JSON-RPC 请求处理 |
| `mcp_server.go` | MCP tool 注册和 schema 定义 |
| `browser/browser.go` | 浏览器工厂，加载 cookies |
| `cookies/cookies.go` | Cookie 文件读写，路径解析 |
| `xiaohongshu/login.go` | 登录检查、QR 获取、扫码等待 |
| `xiaohongshu/search.go` | 搜索功能 |
| `xiaohongshu/publish.go` | 发布功能 |
| `xiaohongshu/feeds.go` | Feed 列表 |
| `headless_browser` (外部依赖) | go-rod 封装，stealth mode |

源码仓库已克隆至 `/Volumes/Work/Projects/xiaohongshu-mcp`。
