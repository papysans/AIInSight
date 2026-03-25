## 1. 修复登录状态误判

- [x] 1.1 修改 `app/services/xiaohongshu_publisher.py` 的 `check_login_status()` 方法：将 ShunL 返回的 text content 尝试 JSON 解析，读取 `loggedIn` 布尔字段判断登录状态；JSON 解析失败时降级为 `logged_in=False`
- [x] 1.2 确保 `get_status()` 返回的 `login_status` 字段与实际状态一致（取决于 1.1 的修复）

## 2. 修复 AI Daily 标题超长

- [x] 2.1 修改 `app/services/publish/ai_daily_publish_service.py` 的 `_default_ranking_title()` 函数：生成不超过 20 字符的标题（如将 `"2026-03-24 AI 热点榜单 Top 10"` 改为 `"3/24 AI热点榜Top10"` 格式）
- [x] 2.2 在 ranking publish 链路中增加标题长度校验：如果最终标题超过 20 字符，自动截断到 20 字符

## 3. 验证

- [x] 3.1 重建 Docker api 容器，验证 `GET /api/xhs/status` 在未登录时正确返回 `login_status: false`
- [x] 3.2 验证完整登录流程：`GET /api/xhs/login-qrcode` → 扫码 → `GET /api/xhs/check-login-session/{sessionId}` → status=logged_in, inner_status=success ✅（注：多账号存在时 `check_auth_status` 无法自动选择账号，需指定 account_id，此问题归入 cloud-remote-mcp-gateway 多账号管理范畴）
- [x] 3.3 验证 AI Daily ranking 发布：标题 `"3/24 AI热点榜Top10"` = 15 字符，通过 ShunL 20 字符校验 ✅

## 4. 修复卡片图片发布链路

- [x] 4.1 修改 `docker-compose.yml`：为 `xhs-mcp` 服务挂载 `./runtime/xhs/images:/app/images`，使 API 容器写入的卡片图片能被 ShunL sidecar 读取
- [x] 4.2 验证共享卷修复：`api` 与 `xhs-mcp` 两个容器都能看到同一批 `/app/images` 图片文件，`No valid image files found` 错误消失

## 5. 修复 legacy publish 兼容层

- [x] 5.1 修改 `xhs-mcp-entrypoint.mjs`：覆盖 ShunL 旧的 `PUBLISH_SELECTORS.publishBtn`，从 `button.publishBtn` 扩展为 `button.publishBtn, div.publish-page-publish-btn button.bg-red` 以匹配当前小红书发布页 DOM
- [x] 5.2 验证当前发布页 DOM：上传图文模式下真实发布按钮位于 `div.publish-page-publish-btn` 容器内，按钮文本为 `发布`
- [x] 5.3 修改 `xhs-mcp-entrypoint.mjs`：将 legacy `xhs_publish_content` 兼容路径写库时的 `noteType` 从非法值 `normal` 改为合法值 `image`，修复 `CHECK constraint failed: note_type IN ('image', 'video')`

## 6. 修复发布结果归一化

- [x] 6.1 修改 `app/services/xiaohongshu_publisher.py`：当 MCP transport 成功但内层 JSON 返回 `{"success": false, ...}` 或 `{"result": {"success": false, ...}}` 时，向上游返回 `success: false`，不再误报外层成功
- [x] 6.2 新增并通过 `tests/services/test_xiaohongshu_publisher.py` 回归测试，覆盖 nested inner failure 与 top-level inner failure 两种场景

## 7. 端到端验证

- [x] 7.1 运行 `pytest -q tests/services/test_xiaohongshu_publisher.py tests/services/test_ai_daily_publish_service.py`，共 12 项测试通过
- [x] 7.2 重建 `xhs-mcp` 与 `api` 容器后重新执行 `POST /api/ai-daily/ranking/publish`
- [x] 7.3 验证 ShunL runtime 日志：图片上传成功、标题填写成功、正文填写成功、标签添加成功、发布按钮点击成功、`Publish successful {}`
- [x] 7.4 验证 ShunL `published_notes` 表：新增一条 `note_type='image'`, `status='published'`, `title='3/24 AI热点榜Top10'` 的发布记录
