---
name: ai-topic-analyzer
description: AI 话题分析助手。适用于“帮我看看 xxx 这个 AI 话题”“深挖这个模型/公司/论文/项目”“做成卡片/发布到小红书”等请求。默认走 AI 证据检索 + 多 Agent 分析，不再询问平台。
---

# AI Topic Analyzer

用于单个 AI 话题的证据检索、辩论式分析、卡片生成与发布。

## 关键规则

- 默认直接调用 `analyze_topic(topic, depth="standard", image_count=0)`，不要先追问平台或图片数量
- 只有用户明确要求时，才额外指定 `depth`、`source_groups` 或 `source_names`
- `analyze_topic` 启动成功后，必须持续调用 `get_analysis_status` 直到任务完成或失败
- 任务完成后，必须调用 `get_analysis_result` 展示结果预览
- 生成卡片是显式后处理步骤，需要调用 `generate_topic_cards`
- 只有用户明确确认后，才能调用 `publish_to_xhs`
- 如果发布失败或返回 `already_published=true`，不要重新调用 `analyze_topic`

## 默认流程

### 1. 启动分析

当用户说“帮我看看 xxx 这个话题”时，直接调用：

```json
{
  "topic": "话题内容",
  "depth": "standard",
  "image_count": 0
}
```

只有在用户明确要求“快速看一眼”“深度研究”“只看社区/论文/代码来源”时，才覆盖默认参数。

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

如果用户明确要求发布，再调用：

```json
{
  "job_id": "job_xxx"
}
```

对应工具：`publish_to_xhs`

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
  "job_id": "job_xxx"
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
