---
name: ai-topic-analyzer
description: AI 话题分析助手。适用于“帮我看看 xxx 这个 AI 话题”“深挖这个模型/公司/论文/项目”“做成卡片/发布到小红书”等请求。默认先确认分析模式，再走 AI 证据检索 + 多 Agent 分析。
---

# AI Topic Analyzer

用于单个 AI 话题的证据检索、辩论式分析、卡片生成与发布。

## 远程 Gateway / 本地开发 两种运行模式

默认优先按 **远程 MCP Gateway** 理解运行环境；只有在本地开发或自托管场景下，才回落到四容器栈。

### 1. 远程 Gateway（优先）

- 用户只连接一个 MCP 地址
- 使用 API key 标识 account
- 单话题分析优先走：`retrieve_and_report` → 宿主端 debate → `submit_analysis_result`
- `analyze_topic` 保留为不支持宿主端 debate 的客户端的回退路径

### 2. 本地开发 / 自托管

如果当前任务明确处于本地开发/自托管环境，再按四容器栈理解：

- `api` → `8000`
- `mcp` → `18061`
- `renderer` → `3001`
- `xhs-mcp` → `18060`

优先使用下面这组命令恢复运行环境：

```bash
docker compose up -d --build api mcp renderer xhs-mcp
docker compose ps
docker compose logs --tail=60 mcp
```

如果 `api` 起不来并提示 `8000` 端口被占，优先怀疑旧 worktree 项目容器还没停干净；如果 `mcp` 容器起不来，先看 `mcp` 日志，不要只盯 `xhs-mcp`。

## 关键规则

- 不要在用户只给出话题时立刻调用 `analyze_topic`
- 如果客户端支持宿主端多轮思考，优先使用 split path：`retrieve_and_report` + 宿主端 debate + `submit_analysis_result`
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
- 如果发布前发现小红书未登录，或发布结果返回 `login_required=true`，先调用 `check_xhs_status`，然后按下方「小红书登录」章节引导用户获取二维码并保留 `session_id`
- 用户扫码后，优先调用 `check_xhs_login_session(session_id)`；若要求短信验证码，再调用 `submit_xhs_verification(session_id, code)`
- 用户扫码完成前不要自动重试发布；等待用户确认后再继续
- 真实发布会对外创建笔记，仍然需要用户明确确认，不要把“登录成功”当成“自动可以发布”
- 如果 `mcp` 容器日志出现 `ImportError: cannot import name 'reset_xhs_login' from 'opinion_mcp.tools'`，说明当前镜像没有带上最新导出修复，需要重新 `docker compose up -d --build api mcp renderer xhs-mcp`

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

如果用户回复“默认”，优先使用 split path：

1. 调用 `retrieve_and_report`
2. 在宿主端完成 analyst/debater 辩论
3. 调用 `submit_analysis_result`

如果当前客户端不支持宿主端 debate，再回退到 `analyze_topic`。

宿主端 debate 的最小执行规则：

- **Analyst**：基于 `topic + news_content + source_stats` 先产出第一版结构化分析
- **Debater**：只做反驳、补盲点、挑证据问题；如果分析已经充分，明确回复 `PASS`
- **终止条件**：debater 回复包含 `PASS`，或达到 `max_rounds / debate_rounds`
- **结束后**：把 `final_analysis + debate_history` 交给 `submit_analysis_result`

建议使用下面的宿主端模板：

- Analyst prompt："基于 reporter 提供的事实摘要与来源分布，输出一版可被挑战的结构化分析，避免直接写成社媒文案。"
- Debater prompt："站在反方角度，指出这版分析中证据不足、推断过度、遗漏变量或更强解释；如果没有实质问题，回复 PASS。"

回退到 `analyze_topic` 的场景：

- 当前客户端不能稳定执行宿主端多轮思考
- 用户明确要求“一步完成，不分步”
- `retrieve_and_report` 或 `submit_analysis_result` 任一步骤失败

回退时调用：

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

如果用户说“登录小红书”“小红书登录”“扫码登录”，按以下流程：

1. 调用 `check_xhs_status` 检查状态，若已登录则告知无需操作
2. 若未登录，调用 `get_xhs_login_qrcode` 并保留返回的 `session_id`
3. 如果客户端能显示图片，直接提示用户用小红书 App 扫码
4. 如果客户端不能直接显示图片，提示用户打开返回的 `qr_image_url`、`qr_image_route` 或 `qr_image_path`
5. 用户扫码后，调用 `check_xhs_login_session(session_id)` 检查状态
6. 若返回需要验证码，调用 `submit_xhs_verification(session_id, code)`
7. 登录成功后再继续发布链路

对应工具：`check_xhs_status` + `get_xhs_login_qrcode` + `check_xhs_login_session` + `submit_xhs_verification`

## 工具

### retrieve_and_report

```json
{
  "topic": "AI 话题内容",
  "depth": "standard",
  "source_groups": ["media"]
}
```

### submit_analysis_result

```json
{
  "topic": "AI 话题内容",
  "news_content": "reporter 输出",
  "final_analysis": "宿主端最终分析",
  "debate_history": ["Analyst round 1", "Debater round 1"],
  "source_stats": {"hn": 2},
  "image_count": 0,
  "xhs_publish_enabled": false
}
```

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

### get_xhs_login_qrcode

获取登录二维码。
```json
{}
```

若返回中包含 `qr_image_url`、`qr_image_route` 或 `qr_image_path`，应优先把这些信息展示给用户，方便在无法直接显示图片的客户端中手动打开二维码。
同时保留返回的 `session_id`，用于后续会话轮询和验证码提交。

### check_xhs_login_session

```json
{
  "session_id": "sess_xxx"
}
```

### submit_xhs_verification

```json
{
  "session_id": "sess_xxx",
  "code": "123456"
}
```

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
