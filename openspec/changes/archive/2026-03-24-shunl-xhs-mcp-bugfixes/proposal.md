## Why

`shunl-xhs-mcp-integration` 完成后，实际联调中发现 5 个 bug：

1. **登录状态误判** — `check_login_status()` 用 `"logged in" in text.lower()` 判断是否已登录，但 ShunL 返回 `"Not logged in (login button visible)"` 也包含 `"logged in"` 子串，导致未登录被误判为已登录
2. **AI Daily 标题超长** — 自动生成的标题（如 `"2026-03-24 AI 热点榜单 Top 10"`，25 字符）超过 ShunL `xhs_publish_content` 的 20 字符限制，导致发布直接报错 `too_big`
3. **发布链路未拦截未登录** — `publish_content()` 依赖 `check_login_status()` 的结果判断是否需要登录，但因 bug 1 的误判，未登录时仍尝试发布，最终被 ShunL 拒绝
4. **卡片图片跨容器不可见** — API 容器将渲染后的卡片写入 `./runtime/xhs/images`，但 `xhs-mcp` 容器未挂载对应 volume，导致 ShunL 报 `No valid image files found`
5. **legacy publish 兼容层已过期** — 本地 `xhs-mcp-entrypoint.mjs` 复活的 `xhs_publish_content` 仍依赖旧版发布页 selector（`button.publishBtn`）和非法 `noteType='normal'`，在当前小红书创作页上会触发 `Publish button not found` 和 SQLite `CHECK constraint failed`

核心痛点：**登录检测的字符串匹配逻辑与 ShunL 的实际返回格式不兼容。**

## What Changes

- **修复** `XiaohongshuPublisher.check_login_status()` 和 `check_login_session()` 的状态判断逻辑：改为解析 ShunL 返回的 JSON 结构，而非字符串子串匹配
- **修复** AI Daily ranking 发布链路的标题长度处理：自动截断或生成符合 20 字符限制的标题
- **修复** `docker-compose.yml` 中 `xhs-mcp` 的图片共享卷挂载，使 API 生成的卡片图片能被 ShunL sidecar 读取
- **修复** 本地 `xhs-mcp-entrypoint.mjs` 里的 legacy publish 兼容逻辑：更新发布按钮 selector，修正 `noteType='image'`
- **修复** `XiaohongshuPublisher.publish_content()` 的结果归一化：transport 成功但内层 publish 失败时，向上游返回 `success: false`
- **验证** 修复后的完整登录 → AI Daily ranking 真发布流程

### Modified Capabilities
- `shunl-xhs-mcp-adapter`: 登录状态检查从字符串匹配改为 JSON 字段解析
- `ai-daily-topic-analysis`: 发布标题自动适配 ShunL 的 20 字符限制
- `docker-first-official-xhs-runtime`: API 渲染图片与 `xhs-mcp` sidecar 之间通过共享 volume 传递卡片文件

## Impact

- **代码影响**: `app/services/xiaohongshu_publisher.py`、`app/services/publish/ai_daily_publish_service.py`、`docker-compose.yml`、`xhs-mcp-entrypoint.mjs`、相关测试文件
- **风险**: 极低，都是 bugfix，不涉及接口变更
- **依赖**: 无新增依赖
