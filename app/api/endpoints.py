from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from loguru import logger
from app.schemas import (
    TopicAnalysisRequest, AgentState, ConfigResponse, ConfigUpdateRequest,
    UserSettingsResponse, UserSettingsUpdateRequest,
    OutputFileListResponse, OutputFileInfo, OutputFileContentResponse,
    WorkflowStatusResponse, LLMProviderConfig,
    XhsPublishRequest,
    TitleCardRenderRequest, RadarCardRenderRequest,
    TimelineCardRenderRequest, TrendCardRenderRequest, ImpactCardRenderRequest,
    DailyRankCardRenderRequest, HotTopicCardRenderRequest, CardRenderResponse,
    AiDailyCollectRequest, AiDailyResponse, AiDailyTopicDetailResponse,
    AiDailyAnalyzeRequest, AiDailyCardsRequest, AiDailyPublishRequest,
    AiDailyRankingCardsRequest, AiDailyRankingPublishRequest,
    TopicCardsRequest,
)
from app.services.workflow import app_graph
from app.services.workflow_status import workflow_status
from app.services.user_settings import load_user_settings, update_user_settings
from app.services.topic_card_builder import (
    build_topic_impact_payload,
    build_topic_radar_payload,
    build_topic_timeline,
)
from app.config import settings
from pathlib import Path
from datetime import datetime
import asyncio
import copy

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "aiinsight-backend"}


@router.post("/analyze")
async def analyze_topic(request: TopicAnalysisRequest):
    """执行完整的话题分析工作流"""
    # Resolve depth preset
    depth = request.depth or "standard"
    depth_cfg = settings.DEPTH_PRESETS.get(depth, settings.DEPTH_PRESETS["standard"])
    debate_rounds = request.debate_rounds if request.debate_rounds is not None else depth_cfg.get("debate_rounds", 2)
    if debate_rounds < 0 or debate_rounds > 5:
        raise HTTPException(status_code=400, detail="debate_rounds 必须在 0-5 之间")

    image_count = request.image_count if request.image_count is not None else 0
    if image_count < 0 or image_count > 9:
        raise HTTPException(status_code=400, detail="image_count 必须在 0-9 之间")

    logger.info(f"[analyze] topic='{request.topic}', depth={depth}, debate_rounds={debate_rounds}, image_count={image_count}")

    await workflow_status.start_workflow(request.topic)

    async def event_generator():
        initial_state = {
            "topic": request.topic,
            "source_groups": request.source_groups or settings.DEFAULT_SOURCE_GROUPS,
            "source_names": request.source_names,
            "depth": depth,
            "debate_rounds": debate_rounds,
            "image_count": image_count,
            "messages": [],
            "evidence_bundle": None,
            "source_stats": {},
        }

        try:
            async for event in app_graph.astream(initial_state):
                for node_name, state_update in event.items():
                    await workflow_status.update_step(node_name)

                    messages = state_update.get("messages", [])
                    content = str(messages[-1]) if messages else "Processing..."

                    node_name_map = {
                        "source_retriever": "Evidence Retriever",
                        "reporter": "Reporter",
                        "analyst": "Analyst",
                        "debater": "Debater",
                        "writer": "Writer",
                        "image_generator": "Image Generator",
                    }
                    display_name = node_name_map.get(node_name, node_name.capitalize())

                    # Extract source stats
                    source_stats = state_update.get("source_stats") if node_name == "source_retriever" else None

                    final_copy = None
                    if node_name == "writer":
                        final_copy = state_update.get("final_copy")
                        if not final_copy and messages:
                            last_msg = str(messages[-1])
                            if "Writer:" in last_msg:
                                final_copy = last_msg.replace("Writer:", "").strip()

                    image_urls = state_update.get("image_urls")

                    agent_state = AgentState(
                        agent_name=display_name,
                        step_content=content,
                        status="thinking",
                        image_urls=image_urls,
                        dataview_images=state_update.get("dataview_images"),
                        source_stats=source_stats,
                        final_copy=final_copy,
                    )

                    yield f"data: {agent_state.model_dump_json()}\n\n"

            await workflow_status.finish_workflow()

            final_state = AgentState(
                agent_name="System",
                step_content="Analysis Complete",
                status="finished",
            )
            yield f"data: {final_state.model_dump_json()}\n\n"

        except Exception as e:
            await workflow_status.reset()
            error_state = AgentState(
                agent_name="System",
                step_content=f"Error: {str(e)}",
                status="error",
            )
            yield f"data: {error_state.model_dump_json()}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """获取当前配置"""
    llm_providers = {
        "reporter": [LLMProviderConfig(**item) for item in settings.AGENT_CONFIG["reporter"]],
        "analyst": [LLMProviderConfig(**item) for item in settings.AGENT_CONFIG["analyst"]],
        "debater": [LLMProviderConfig(**item) for item in settings.AGENT_CONFIG["debater"]],
        "writer": [LLMProviderConfig(**item) for item in settings.AGENT_CONFIG["writer"]],
    }

    return ConfigResponse(
        llm_providers=llm_providers,
        debate_max_rounds=settings.DEBATE_MAX_ROUNDS,
        default_source_groups=settings.DEFAULT_SOURCE_GROUPS,
        available_sources=list(settings.get_available_sources()),
    )


@router.put("/config")
async def update_config(request: ConfigUpdateRequest):
    """更新配置（部分更新）"""
    updated_fields = []

    if request.debate_max_rounds is not None:
        if request.debate_max_rounds < 1:
            raise HTTPException(status_code=400, detail="debate_max_rounds 必须大于0")
        settings.DEBATE_MAX_ROUNDS = request.debate_max_rounds
        updated_fields.append("debate_max_rounds")

    if not updated_fields:
        raise HTTPException(status_code=400, detail="没有提供要更新的字段")

    return {
        "success": True,
        "message": f"配置已更新: {', '.join(updated_fields)}",
        "updated_fields": updated_fields,
    }


@router.get("/user-settings", response_model=UserSettingsResponse)
async def get_user_settings():
    """获取前端可写入的用户设置（存储在 cache/user_settings.json）"""
    data = load_user_settings()
    return UserSettingsResponse(
        llm_apis=data.get("llm_apis") or [],
        volcengine=data.get("volcengine"),
        agent_llm_overrides=data.get("agent_llm_overrides") or {},
    )


@router.put("/user-settings", response_model=UserSettingsResponse)
async def put_user_settings(request: UserSettingsUpdateRequest):
    """更新前端可写入的用户设置（部分更新）"""
    if request.llm_apis is not None:
        for api in request.llm_apis:
            provider_key = api.providerKey
            model = api.model
            if model and provider_key and not settings.validate_model(provider_key, model):
                available_models = settings.get_models_for_provider(provider_key)
                model_names = [item["id"] for item in available_models] if available_models else []
                raise HTTPException(
                    status_code=400,
                    detail=f"模型 {model} 在提供商 {provider_key} 中无效。可用模型: {', '.join(model_names)}",
                )

    if request.agent_llm_overrides is not None:
        for agent_key, override in request.agent_llm_overrides.items():
            if not isinstance(override, dict):
                continue
            provider = override.get("provider")
            model = override.get("model")
            if provider and model and not settings.validate_model(provider, model):
                available_models = settings.get_models_for_provider(provider)
                model_names = [item["id"] for item in available_models] if available_models else []
                raise HTTPException(
                    status_code=400,
                    detail=f"Agent {agent_key} 的模型 {model} 在提供商 {provider} 中无效。可用模型: {', '.join(model_names)}",
                )

    merged = update_user_settings(
        llm_apis=[api.model_dump() for api in request.llm_apis] if request.llm_apis is not None else None,
        volcengine=request.volcengine.model_dump() if request.volcengine is not None else None,
        agent_llm_overrides=request.agent_llm_overrides,
    )

    return UserSettingsResponse(
        llm_apis=merged.get("llm_apis") or [],
        volcengine=merged.get("volcengine"),
        agent_llm_overrides=merged.get("agent_llm_overrides") or {},
    )


@router.get("/outputs", response_model=OutputFileListResponse)
async def get_output_files(limit: int = 20, offset: int = 0):
    """获取历史输出文件列表"""
    output_dir = Path("outputs")
    if not output_dir.exists():
        return OutputFileListResponse(files=[], total=0)
    
    # 获取所有 .md 文件
    md_files = list(output_dir.glob("*.md"))
    
    # 排除 TECH_DOC.md
    md_files = [f for f in md_files if f.name != "TECH_DOC.md"]
    
    # 按修改时间排序（最新的在前）
    md_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    
    # 分页
    total = len(md_files)
    paginated_files = md_files[offset:offset + limit]
    
    # 构建文件信息
    file_infos = []
    for file_path in paginated_files:
        stat = file_path.stat()
        # 从文件名提取主题和时间
        # 格式: YYYY-MM-DD_HH-MM-SS_主题.md
        parts = file_path.stem.split("_", 2)
        if len(parts) >= 3:
            topic = parts[2]
        else:
            topic = file_path.stem
        
        file_infos.append(OutputFileInfo(
            filename=file_path.name,
            topic=topic,
            created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            size=stat.st_size
        ))
    
    return OutputFileListResponse(files=file_infos, total=total)


@router.get("/outputs/{filename}", response_model=OutputFileContentResponse)
async def get_output_file(filename: str):
    """获取指定输出文件的内容"""
    # 安全检查：防止路径遍历攻击
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="无效的文件名")
    
    file_path = Path("outputs") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail="不是有效的文件")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        stat = file_path.stat()
        created_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        return OutputFileContentResponse(
            filename=filename,
            content=content,
            created_at=created_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.get("/workflow/status", response_model=WorkflowStatusResponse)
async def get_workflow_status():
    """获取当前工作流状态"""
    status = await workflow_status.get_status()
    return WorkflowStatusResponse(**status)


# --- 模型管理接口 ---

@router.get("/models")
async def get_models():
    """获取所有提供商的模型列表
    
    返回格式：
    {
        "deepseek": [
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "description": "...", "type": "chat", "is_default": true},
            ...
        ],
        "gemini": [...],
        ...
    }
    """
    models = settings.get_all_models()
    return models


@router.post("/validate-model")
async def validate_model(payload: dict):
    """验证提供商-模型组合是否有效
    
    请求体：
    {
        "provider": "deepseek",
        "model": "deepseek-chat"
    }
    
    返回：
    {
        "valid": true/false,
        "message": "验证消息"
    }
    """
    provider = payload.get("provider", "").strip()
    model = payload.get("model", "").strip()
    
    if not provider or not model:
        return {
            "valid": False,
            "message": "提供商和模型参数不能为空"
        }
    
    is_valid = settings.validate_model(provider, model)
    
    if is_valid:
        return {
            "valid": True,
            "message": f"模型 {model} 在提供商 {provider} 中有效"
        }
    else:
        # 获取该提供商的可用模型列表
        available_models = settings.get_models_for_provider(provider)
        if available_models:
            model_names = [m["id"] for m in available_models]
            return {
                "valid": False,
                "message": f"模型 {model} 在提供商 {provider} 中无效。可用模型: {', '.join(model_names)}"
            }
        else:
            return {
                "valid": False,
                "message": f"提供商 {provider} 不存在或没有可用模型"
            }


# --- 小红书 MCP 发布接口 ---

@router.get("/xhs/status")
async def get_xhs_status():
    """检查小红书 MCP 服务状态和登录状态"""
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher
    from app.schemas import XhsStatusResponse
    
    status = await xiaohongshu_publisher.get_status()
    return XhsStatusResponse(
        mcp_available=status.get("mcp_available", False),
        login_status=status.get("login_status", False),
        message=status.get("message", "")
    )


@router.post("/xhs/publish")
async def publish_to_xhs(request: XhsPublishRequest):
    """手动发布内容到小红书
    
    请求体：
    - title: 标题
    - content: 正文内容
    - images: 图片列表（本地路径或 HTTP URL）
    """
    from app.services.xiaohongshu_publisher import xiaohongshu_publisher
    from app.schemas import XhsPublishRequest, XhsPublishResponse
    
    if not request.title or not request.content:
        return XhsPublishResponse(
            success=False,
            message="标题和内容不能为空"
        )
    
    if not request.images:
        return XhsPublishResponse(
            success=False,
            message="至少需要一张图片"
        )
    
    result = await xiaohongshu_publisher.publish_content(
        title=request.title,
        content=request.content,
        images=request.images,
        tags=request.tags
    )
    
    return XhsPublishResponse(
        success=result.get("success", False),
        message=result.get("message") or result.get("error", "发布失败"),
        data=result.get("data")
    )


# ============================================================
# Card Render API (proxy to renderer service)
# ============================================================
from app.services.card_render_client import card_render_client


@router.post("/cards/title", response_model=CardRenderResponse)
async def render_title_card(request: TitleCardRenderRequest):
    """渲染标题卡"""
    result = await card_render_client.render_title(
        title=request.title,
        emoji=request.emoji,
        theme=request.theme,
        emoji_position=request.emoji_position,
    )
    return CardRenderResponse(**result)


@router.post("/cards/impact", response_model=CardRenderResponse)
async def render_impact_card(request: ImpactCardRenderRequest):
    """渲染影响判断卡"""
    result = await card_render_client.render_impact(
        title=request.title,
        summary=request.summary,
        insight=request.insight,
        signals=request.signals,
        actions=request.actions,
        confidence=request.confidence,
        tags=request.tags,
    )
    return CardRenderResponse(**result)


@router.post("/cards/radar", response_model=CardRenderResponse)
async def render_radar_card(request: RadarCardRenderRequest):
    """渲染雷达图卡"""
    result = await card_render_client.render_radar(
        labels=request.labels,
        datasets=[d if isinstance(d, dict) else d.model_dump() for d in request.datasets],
    )
    return CardRenderResponse(**result)


@router.post("/cards/timeline", response_model=CardRenderResponse)
async def render_timeline_card(request: TimelineCardRenderRequest):
    """渲染辩论时间线卡"""
    result = await card_render_client.render_timeline(timeline=request.timeline)
    return CardRenderResponse(**result)


@router.post("/cards/trend", response_model=CardRenderResponse)
async def render_trend_card(request: TrendCardRenderRequest):
    """渲染趋势图卡"""
    result = await card_render_client.render_trend(
        stage=request.stage,
        growth=request.growth,
        curve=request.curve,
    )
    return CardRenderResponse(**result)


@router.post("/cards/daily-rank", response_model=CardRenderResponse)
async def render_daily_rank_card(request: DailyRankCardRenderRequest):
    """渲染每日榜单卡"""
    result = await card_render_client.render_daily_rank(
        date=request.date,
        topics=[t if isinstance(t, dict) else t.model_dump() for t in request.topics],
        title=request.title,
    )
    return CardRenderResponse(**result)


@router.post("/cards/hot-topic", response_model=CardRenderResponse)
async def render_hot_topic_card(request: HotTopicCardRenderRequest):
    """渲染热点详情卡"""
    result = await card_render_client.render_hot_topic(
        title=request.title,
        summary=request.summary,
        tags=request.tags,
        source_count=request.source_count,
        score=request.score,
        date=request.date,
        sources=request.sources,
    )
    return CardRenderResponse(**result)


# ============================================================
# 话题分析卡片生成
# ============================================================

@router.post("/topic/cards")
async def generate_topic_cards(request: TopicCardsRequest):
    """为话题分析结果生成可视化卡片"""
    cards = {}
    radar_payload = build_topic_radar_payload(
        source_stats=request.source_stats,
        fallback_sources=request.sources,
    )
    timeline_payload = build_topic_timeline(
        output_file=request.output_file,
        timeline=request.timeline,
        title=request.title,
        summary=request.summary,
        insight=request.insight,
    )
    impact_payload = build_topic_impact_payload(
        title=request.title,
        summary=request.summary,
        insight=request.insight,
        tags=request.tags,
        source_stats=request.source_stats,
        timeline=timeline_payload,
    )

    for ct in request.card_types:
        if ct == "title":
            result = await card_render_client.render_title(title=request.title)
            cards["title"] = CardRenderResponse(**result)
        elif ct == "impact":
            result = await card_render_client.render_impact(**impact_payload)
            cards["impact"] = CardRenderResponse(**result)
        elif ct == "radar":
            result = await card_render_client.render_radar(
                labels=radar_payload["labels"],
                datasets=radar_payload["datasets"],
            )
            cards["radar"] = CardRenderResponse(**result)
        elif ct == "timeline":
            result = await card_render_client.render_timeline(timeline=timeline_payload)
            cards["timeline"] = CardRenderResponse(**result)
        elif ct == "hot-topic":
            result = await card_render_client.render_hot_topic(
                title=request.title,
                summary=request.summary,
                tags=request.tags[:6],
                source_count=request.source_count,
                score=request.score,
                sources=request.sources[:4],
            )
            cards["hot-topic"] = CardRenderResponse(**result)
    return {"cards": cards}


# ============================================================
# AI Daily Pipeline API
# ============================================================
from app.services.ai_daily_pipeline import collect_ai_daily, get_topic_by_id


@router.post("/ai-daily/collect", response_model=AiDailyResponse)
async def ai_daily_collect(request: AiDailyCollectRequest = None):
    """触发 AI 日报采集 pipeline（collect → score → cluster → cache）"""
    req = request or AiDailyCollectRequest()
    result = await collect_ai_daily(
        force_refresh=req.force_refresh,
        source_names=req.sources,
    )
    return result


@router.get("/ai-daily", response_model=AiDailyResponse)
async def ai_daily_get():
    """获取今日 AI 日报（优先读缓存）"""
    result = await collect_ai_daily(force_refresh=False)
    return result


@router.get("/ai-daily/{topic_id}", response_model=AiDailyTopicDetailResponse)
async def ai_daily_topic_detail(topic_id: str):
    """获取单个话题的详情"""
    topic = await get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")
    return AiDailyTopicDetailResponse(topic=topic)


@router.post("/ai-daily/{topic_id}/analyze")
async def ai_daily_analyze_topic(topic_id: str, request: AiDailyAnalyzeRequest = None):
    """对单个 AI 话题运行深度分析 workflow"""
    topic = await get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    depth = (request.depth if request else None) or "standard"

    # Convert topic to NewsRequest-compatible input and run workflow
    from app.services.ai_daily_workflow_adapter import topic_to_workflow_input
    workflow_input = topic_to_workflow_input(topic, depth=depth)

    # Run the existing analysis workflow
    result = await app_graph.ainvoke(workflow_input)
    return {
        "topic_id": topic_id,
        "depth": depth,
        "analysis": result,
    }


def _topic_to_rank_item(topic, rank: int) -> dict:
    """Map DailyTopic to the {rank, title, score, tags} shape the renderer expects."""
    return {
        "rank": rank,
        "title": topic.title,
        "score": topic.final_score,
        "tags": (topic.tags or [])[:3],
    }


def _topic_to_hot_topic_payload(topic) -> dict:
    """Map DailyTopic to the hot-topic card payload."""
    return {
        "title": topic.title,
        "summary": topic.summary_zh,
        "tags": (topic.tags or [])[:6],
        "source_count": topic.source_count or len(topic.sources or []),
        "score": topic.final_score,
        "sources": [s.source for s in (topic.sources or [])[:4] if getattr(s, "source", None)],
    }


@router.post("/ai-daily/ranking/cards")
async def ai_daily_ranking_cards(request: AiDailyRankingCardsRequest = None):
    """为今日 AI 热点整榜生成卡片套图"""
    from app.services.publish.ai_daily_publish_service import generate_ai_daily_ranking_cards
    req = request or AiDailyRankingCardsRequest()
    result = await generate_ai_daily_ranking_cards(
        limit=req.limit,
        title=req.title,
        card_types=req.card_types,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Card generation failed"))
    return result


@router.post("/ai-daily/ranking/publish")
async def ai_daily_ranking_publish(request: AiDailyRankingPublishRequest = None):
    """将今日 AI 热点整榜发布到小红书"""
    from app.services.publish.ai_daily_publish_service import publish_ai_daily_ranking
    req = request or AiDailyRankingPublishRequest()
    result = await publish_ai_daily_ranking(
        limit=req.limit,
        title=req.title,
        content=req.content,
        tags=req.tags,
        card_types=req.card_types,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Publish failed"))
    return result


@router.post("/ai-daily/{topic_id}/cards")
async def ai_daily_topic_cards(topic_id: str, request: AiDailyCardsRequest = None):
    """为单个话题生成卡片套图"""
    topic = await get_topic_by_id(topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail=f"Topic {topic_id} not found")

    card_types = (request.card_types if request else None) or ["title", "hot-topic"]
    cards = {}

    for ct in card_types:
        if ct == "title":
            result = await card_render_client.render_title(title=topic.title)
            cards["title"] = CardRenderResponse(**result)
        elif ct == "hot-topic":
            result = await card_render_client.render_hot_topic(**_topic_to_hot_topic_payload(topic))
            cards["hot-topic"] = CardRenderResponse(**result)
        elif ct == "daily-rank":
            from datetime import date as date_cls
            result = await card_render_client.render_daily_rank(
                date=date_cls.today().isoformat(),
                topics=[_topic_to_rank_item(topic, 1)],
            )
            cards["daily-rank"] = CardRenderResponse(**result)

    return {"topic_id": topic_id, "cards": cards}


@router.post("/ai-daily/{topic_id}/publish")
async def ai_daily_publish(topic_id: str, request: AiDailyPublishRequest = None):
    """将 AI 日报话题发布到小红书"""
    from app.services.publish.ai_daily_publish_service import publish_ai_daily_topic
    req = request or AiDailyPublishRequest()
    result = await publish_ai_daily_topic(
        topic_id=topic_id,
        title=req.title,
        content=req.content,
        tags=req.tags,
        card_types=req.card_types,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Publish failed"))
    return result
