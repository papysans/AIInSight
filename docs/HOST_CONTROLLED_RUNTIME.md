# Host-Controlled Runtime

This document describes the intended execution model for the new host-controlled analysis path in AIInSight.

## Primary Path

### Freeform topic

Use:

- `host_analyze_topic`

Execution model:

```text
host
  -> resolve_host_sources
  -> retrieve_host_evidence
  -> build_host_analysis_state
  -> run_host_reasoning_pipeline
       -> default_host_reporter
       -> default_host_analyst
       -> default_host_debater
       -> default_host_writer
  -> optional HostCapabilityClient.render_card
  -> optional HostCapabilityClient.publish_note
```

### AI Daily topic

Use:

- `host_analyze_ai_topic`

Execution model:

```text
topic_id
  -> get_topic_by_id
  -> run_default_host_analysis
  -> optional renderer/publish capability calls
```

## Fallback Paths

If the host-controlled path cannot run, fallback in this order:

1. split compatibility path
   - `retrieve_and_report`
   - host debate
   - `submit_analysis_result`
2. legacy backend path
   - `analyze_topic`
   - `analyze_ai_topic`

## When to Prefer Each Path

### Prefer host-controlled path when

- the host runtime has collectors / extraction deps available
- the client can keep local reasoning state
- the goal is simpler cloud state management
- the user wants the full reasoning chain controlled locally

### Prefer split compatibility path when

- the host can do reasoning but not retrieval/extraction reliably
- migration is still in progress
- you need to reuse current cloud front-half behavior temporarily

### Prefer legacy backend path when

- the client cannot support host-local analysis execution
- you need the existing asynchronous backend workflow/job model

## Capability Backend Responsibilities

Even in host-controlled mode, cloud capability services remain responsible for:

- API key / account mapping
- renderer
- XHS runtime / login / publish
- artifact serving
- optional image generation
- optional AI Daily shared collect/cache

## Current Code Entry Points

- `opinion_mcp/services/xiaohongshu_publisher.py` — XHS MCP 直连客户端
- `opinion_mcp/services/card_render_client.py` — 渲染服务直连客户端
- `opinion_mcp/tools/publish.py` — XHS 发布/登录 MCP 工具
- `opinion_mcp/tools/render.py` — 卡片渲染 MCP 工具
- `opinion_mcp/server.py` — MCP tool registration

## Recommended Future Wiring

If the project wants host-controlled mode to become the true default, the next wiring layer should:

1. prefer `host_analyze_topic` / `host_analyze_ai_topic` in skill/runtime entry logic
2. keep split + legacy paths behind explicit fallback rules
3. surface a single user-facing runtime mode decision instead of exposing all three paths equally

## User Experience Reality (Current State)

Today, host-controlled mode means:

- the user installs the skill(s), and
- a local `opinion_mcp` runtime must be available,
- while renderer / XHS publish / artifact services can remain cloud-hosted.

So the current shape is:

```text
Skill (control plane, host-side reasoning)
  -> opinion_mcp (capability plane, 6 tools)
  -> renderer + xhs-mcp (service plane, Docker sidecar)
```

### To reach a true “just install the skills” UX later

The project still needs a bootstrap/packaging layer that can:

1. auto-start or auto-install local `opinion_mcp`
2. verify host dependencies for retrieval/extraction
3. bind the local runtime to cloud capability endpoints
4. hide ports/process management from non-technical users
