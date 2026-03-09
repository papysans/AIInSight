---
name: ai-topic-analyzer
description: AI 话题分析助手。适用于“帮我看看 xxx 这个 AI 话题”“深挖这个模型/公司/论文/项目”“做成卡片/发布到小红书”等请求。默认先确认分析模式，再走 AI 证据检索 + 多 Agent 分析。
---

# AI Topic Analyzer

用于单个 AI 话题的证据检索、辩论式分析、卡片生成与发布。

## 关键规则

- 不要在用户只给出话题时立刻调用 `analyze_topic`
- 先确认分析模式：`quick` / `standard` / `deep` / `自定义来源`
- 不再询问旧的社媒平台；如果用户要自定义，询问的是 AI 来源组或具体来源
- 默认参数是 `depth="standard"`、默认来源组、`image_count=0`
- 如果用户明确要求“3轮/4轮辩论”，才额外传 `debate_rounds`
- 如果用户明确要求“带图/2张图/配图”，才传 `image_count`
- `analyze_topic` 启动成功后，必须持续调用 `get_analysis_status` 直到任务完成或失败
- 任务完成后，必须调用 `get_analysis_result` 展示结果预览
- 生成卡片是显式后处理步骤，需要调用 `generate_topic_cards`
- 只有用户明确确认后，才能调用 `publish_to_xhs`
- 如果发布失败或返回 `already_published=true`，不要重新调用 `analyze_topic`
- 如果发布前发现小红书未登录，或发布结果返回 `login_required=true`，先调用 `check_xhs_status` 确认，然后引导用户从浏览器复制 Cookie（见下方「小红书登录」章节）
- 用户发来 Cookie 后，调用 `upload_xhs_cookies` 注入，确认 `login_verified=true` 后再继续发布
- 注入成功前不要自动重试发布；等待用户确认后再继续
- **禁止调用 `xhs_login` 或 `get_xhs_login_qrcode`**：这两个工具依赖 Docker 内无头浏览器，小红书会拦截，必须走 Cookie 注入流程

## 默认流程

### 1. 启动分析

当用户说“帮我看看 xxx 这个话题”时，先给一个简短确认：

```text
准备分析「xxx」。

可选模式：
- quick：快速看重点
- standard：标准深挖（推荐）
- deep：更深一层
- 自定义来源：media / research / code / community

直接回复“默认”，我就按 standard 开始。
如果你想顺便出图，也可以补一句“带 2 张图”。
```

如果用户回复“默认”，调用：

```json
{
  "topic": "话题内容",
  "depth": "standard",
  "image_count": 0
}
```

只有在用户明确要求“快速看一眼”“深度研究”“只看社区/论文/代码来源”“3轮辩论”“带2张图”时，才覆盖默认参数。

### 2. 轮询状态

- 调用 `get_analysis_status(job_id)`
- 任务运行中时，简要汇报进度和当前步骤
- 持续轮询直到 `status=completed` 或 `status=failed`

### 3. 展示结果

完成后调用 `get_analysis_result(job_id)`，向用户展示：

- 核心观点和深度洞察
- 文案预览
- 已分析来源、跳过来源、证据条数
- 结果文件路径或卡片预览路径

### 4. 后处理

如果用户要求“生成卡片/做图”，调用：

```json
{
  "job_id": "job_xxx"
}
```

对应工具：`generate_topic_cards`

默认优先生成：

```json
{
  "job_id": "job_xxx",
  "card_types": ["title", "impact", "radar", "timeline"]
}
```

如果用户明确要求发布，再调用：

```json
{
  "job_id": "job_xxx"
}
```

对应工具：`publish_to_xhs`

如果用户说“登录小红书”“小红书登录”“注入cookie”，按以下流程：

1. 调用 `check_xhs_status` 检查状态，若已登录则告知无需操作
2. 若未登录，引导用户提取 Cookie：

```
请在电脑浏览器中按以下步骤操作：

1️⃣ 打开 https://www.xiaohongshu.com 并确保已登录
2️⃣ 按 F12 打开开发者工具 → 切到 Network（网络）面板
3️⃣ 刷新页面，在请求列表中点击第一个 `explore` 请求
4️⃣ 在右侧 Headers 中找到 Request Headers → Cookie
5️⃣ 复制完整的 Cookie 值（一长串 key=value; key=value... 的文本）
6️⃣ 把复制的内容发给我
```

3. 用户发来 Cookie 后，调用 `upload_xhs_cookies(cookies_data=用户的字符串)` 注入
4. 检查返回的 `login_verified`，成功则告知用户登录完成

对应工具：`check_xhs_status` + `upload_xhs_cookies`

## 工具

### analyze_topic

```json
{
  "topic": "AI 话题内容",
  "depth": "standard",
  "image_count": 0
}
```

### get_analysis_status

```json
{
  "job_id": "job_xxx",
  "card_types": ["title", "impact", "radar", "timeline"]
}
```

### get_analysis_result

```json
{
  "job_id": "job_xxx"
}
```

### generate_topic_cards

```json
{
  "job_id": "job_xxx"
}
```

### publish_to_xhs

```json
{
  "job_id": "job_xxx"
}
```

### check_xhs_status

检查小红书 MCP 可用性和登录状态。
```json
{}
```

### upload_xhs_cookies

将用户浏览器复制的 Cookie 注入到 xhs-mcp 并验证登录态。
```json
{
  "cookies_data": "用户提供的原始 Cookie 字符串"
}
```

### ~~get_xhs_login_qrcode~~ / ~~xhs_login~~
⛔ **禁止调用**。小红书会拦截 Docker 内无头浏览器。登录必须走 Cookie 注入流程（见「小红书登录」章节）。

## 来源组说明

| 组名 | 包含来源 | 说明 |
|------|---------|------|
| media | aibase, jiqizhixin, qbitai, techcrunch_ai | AI 媒体新闻 |
| research | hf_papers | 论文/研究 |
| code | github_trending | 代码/开源 |
| community | hn, reddit | 社区讨论 |

## 深度预设

| 深度 | 辩论轮数 | 正文提取上限 | 适用场景 |
|------|---------|-------------|---------|
| quick | 0 | 5 | 快速概览 |
| standard | 2 | 10 | 标准分析 |
| deep | 4 | 20 | 深度研究 |
