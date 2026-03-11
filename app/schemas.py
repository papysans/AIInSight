from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import List, Optional, Dict, Any, Union


class TopicAnalysisRequest(BaseModel):
    topic: str
    depth: str = "standard"  # "quick" | "standard" | "deep"
    source_groups: Optional[List[str]] = None  # ["media","research","code","community"]
    source_names: Optional[List[str]] = None  # precise override, e.g. ["aibase", "hn"]
    debate_rounds: Optional[int] = None  # override depth preset if set
    image_count: Optional[int] = 0  # default 0, card generation as follow-up step


# Keep backward-compat alias
NewsRequest = TopicAnalysisRequest


class AgentState(BaseModel):
    agent_name: str
    step_content: str
    status: str  # 'thinking' | 'finished' | 'error'
    model: Optional[str] = None
    image_urls: Optional[List[str]] = None
    dataview_images: Optional[List[str]] = None
    source_stats: Optional[Dict[str, int]] = None  # {source_name: count}
    final_copy: Optional[str] = None


class EvidenceItem(BaseModel):
    """A single piece of evidence with optional full text"""

    source_item: "SourceItem"  # forward ref, defined below
    full_text: Optional[str] = None
    extraction_status: str = "pending"  # "success" | "fallback" | "failed"


class EvidenceBundle(BaseModel):
    """Collection of evidence for a topic analysis"""

    topic: str
    items: List[EvidenceItem] = Field(default_factory=list)
    sources_analyzed: List[str] = Field(default_factory=list)
    skipped_sources: List[str] = Field(default_factory=list)
    source_stats: Dict[str, int] = Field(default_factory=dict)
    evidence_count: int = 0
    from_cache: bool = False


# --- 配置相关 Schema ---
class LLMProviderConfig(BaseModel):
    provider: str
    model: str


class AgentConfig(BaseModel):
    reporter: List[LLMProviderConfig]
    analyst: List[LLMProviderConfig]
    debater: List[LLMProviderConfig]
    writer: List[LLMProviderConfig]


class ConfigResponse(BaseModel):
    llm_providers: Dict[str, List[LLMProviderConfig]]
    debate_max_rounds: int
    default_source_groups: List[str]
    available_sources: List[str]


class ConfigUpdateRequest(BaseModel):
    debate_max_rounds: Optional[int] = None


# --- 前端可写入的用户设置（落盘到 cache/，不影响 .env） ---


class UserLLMApi(BaseModel):
    id: Optional[int] = None
    provider: str
    providerKey: str
    url: Optional[str] = None
    key: str
    model: Optional[str] = None
    active: Optional[bool] = True


class VolcengineConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    image_count: Optional[int] = 2


class UserSettingsResponse(BaseModel):
    llm_apis: List[UserLLMApi] = Field(default_factory=list)
    volcengine: Optional[VolcengineConfig] = None
    agent_llm_overrides: Dict[str, Union[str, Dict[str, Any]]] = Field(
        default_factory=dict
    )


class UserSettingsUpdateRequest(BaseModel):
    llm_apis: Optional[List[UserLLMApi]] = None
    volcengine: Optional[VolcengineConfig] = None
    agent_llm_overrides: Optional[Dict[str, Union[str, Dict[str, Any]]]] = None


# --- 输出文件相关 Schema ---
class OutputFileInfo(BaseModel):
    filename: str
    topic: str
    created_at: str
    size: int


class OutputFileListResponse(BaseModel):
    files: List[OutputFileInfo]
    total: int


class OutputFileContentResponse(BaseModel):
    filename: str
    content: str
    created_at: str


# --- 工作流状态相关 Schema ---
class WorkflowStatusResponse(BaseModel):
    running: bool
    current_step: Optional[str] = None
    progress: int = 0
    started_at: Optional[str] = None
    topic: Optional[str] = None
    current_source: Optional[str] = None  # 当前正在检索的来源


# --- 数据生成相关 Schema (removed: domestic platform-specific) ---


# --- 小红书发布相关 Schema ---
class XhsPublishRequest(BaseModel):
    """小红书发布请求"""

    title: str
    content: str
    images: List[str] = Field(default_factory=list)  # 图片列表（本地路径或 HTTP URL）
    tags: Optional[List[str]] = None  # 话题标签（不含#前缀）


class XhsPublishResponse(BaseModel):
    """小红书发布响应"""

    success: bool
    message: str
    login_required: bool = False
    login_qrcode: Optional[Dict[str, Any]] = None
    qr_image_url: Optional[str] = None
    qr_image_route: Optional[str] = None
    qr_image_path: Optional[str] = None
    expires_at: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class XhsStatusResponse(BaseModel):
    """小红书 MCP 状态响应"""

    mcp_available: bool
    login_status: bool
    message: str


class XhsUploadCookiesRequest(BaseModel):
    """小红书 Cookie 上传请求"""

    cookies: Any  # go-rod cookie JSON array or raw cookies.json content


class XhsUploadCookiesResponse(BaseModel):
    """小红书 Cookie 上传响应"""

    success: bool
    message: str
    login_verified: bool = False


class XhsLoginQrcodeResponse(BaseModel):
    """小红书登录二维码响应"""

    success: bool
    message: str
    qr_image_url: Optional[str] = None
    qr_image_route: Optional[str] = None
    qr_image_path: Optional[str] = None
    qr_preview_url: Optional[str] = None
    qr_ascii: Optional[str] = None
    expires_at: Optional[str] = None
    login_method: Optional[str] = None  # "xhs-mcp" or "playwright"
    session_id: Optional[str] = None  # Playwright login session ID


# ============================================================
# AI Daily Pipeline Schemas
# ============================================================


class SourceItem(BaseModel):
    """采集到的单条原始新闻"""

    id: str
    title: str
    url: str
    source: str  # e.g. "aibase", "jiqizhixin", "github_trending"
    source_type: str  # "media" | "product" | "research" | "code"
    lang: str  # "zh" | "en"
    published_at: Optional[str] = None
    summary: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    extra: Dict[str, Any] = Field(default_factory=dict)


class DailyTopic(BaseModel):
    """聚类后的每日话题"""

    topic_id: str
    title: str
    summary_zh: str
    sources: List[SourceItem] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    source_count: int = 0
    lang_mix: List[str] = Field(default_factory=list)
    ai_relevance_score: float = 0.0
    impact_score: float = 0.0
    freshness_score: float = 0.0
    discussion_score: float = 0.0
    final_score: float = 0.0


class AiDailyCollectRequest(BaseModel):
    """AI Daily 采集请求"""

    force_refresh: bool = False
    sources: Optional[List[str]] = None  # 指定数据源，None=全部


class AiDailyResponse(BaseModel):
    """AI Daily 榜单响应"""

    date: str
    topics: List[DailyTopic] = Field(default_factory=list)
    total: int = 0
    sources_used: List[str] = Field(default_factory=list)
    collected_at: Optional[str] = None


class AiDailyTopicDetailResponse(BaseModel):
    """单条 AI 热点详情"""

    topic: DailyTopic
    related_topics: List[str] = Field(default_factory=list)


class AiDailyAnalyzeRequest(BaseModel):
    """AI 热点分析请求"""

    depth: str = "standard"  # "quick" | "standard" | "deep"
    debate_rounds: Optional[int] = None  # override depth preset
    image_count: int = 0  # default 0, card gen as follow-up


class AiDailyCardsRequest(BaseModel):
    """AI 热点卡片包请求"""

    card_types: List[str] = Field(default_factory=lambda: ["title", "hot-topic"])


class TopicCardsRequest(BaseModel):
    """话题分析卡片生成请求"""

    title: str = ""
    summary: str = ""
    insight: str = ""
    tags: List[str] = Field(default_factory=list)
    source_count: int = 0
    score: float = 0.0
    sources: List[str] = Field(default_factory=list)
    source_stats: Dict[str, int] = Field(default_factory=dict)
    output_file: Optional[str] = None
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    card_types: List[str] = Field(
        default_factory=lambda: ["title", "impact", "radar", "timeline"]
    )


# ============================================================
# Card Render Schemas
# ============================================================


class CardRenderRequest(BaseModel):
    """通用卡片渲染请求基类"""

    model_config = ConfigDict(extra="allow")
    card_type: str  # "title" | "impact" | "radar" | "timeline" | "trend" | "daily_rank"


class TitleCardRenderRequest(BaseModel):
    """标题卡渲染请求"""

    title: str
    emoji: str = "🔍"
    theme: str = "warm"
    emoji_position: Optional[Dict[str, Any]] = None


class RadarCardRenderRequest(BaseModel):
    """雷达图卡渲染请求"""

    labels: List[str]
    datasets: List[Dict[str, Any]]


class TimelineCardRenderRequest(BaseModel):
    """辩论时间线卡渲染请求"""

    timeline: List[Dict[str, Any]]  # [{round, title, summary, insight}]


class TrendCardRenderRequest(BaseModel):
    """趋势图卡渲染请求"""

    stage: str  # "爆发期" | "扩散期" | "回落期"
    growth: int
    curve: List[float]


class DailyRankCardRenderRequest(BaseModel):
    """每日榜单卡渲染请求"""

    date: Optional[str] = None
    topics: List[Dict[str, Any]]  # [{rank, title, score, tags}]
    title: str = "AI 每日热点"


class HotTopicCardRenderRequest(BaseModel):
    """热点详情卡渲染请求"""

    title: str
    summary: str
    tags: List[str] = Field(default_factory=list)
    source_count: int = 0
    score: float = 0.0
    date: Optional[str] = None
    sources: List[str] = Field(default_factory=list)


class ImpactCardRenderRequest(BaseModel):
    """单话题影响与跟进卡渲染请求"""

    title: str
    summary: str = ""
    insight: str = ""
    signals: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    confidence: str = ""
    tags: List[str] = Field(default_factory=list)


class CardRenderResponse(BaseModel):
    """卡片渲染统一响应"""

    success: bool
    image_data_url: Optional[str] = None
    image_url: Optional[str] = None
    output_path: Optional[str] = None
    width: int = 1080
    height: int = 1440
    mime_type: str = "image/png"
    error: Optional[str] = None


# ============================================================
# AI Daily Publish Schemas
# ============================================================


class AiDailyPublishRequest(BaseModel):
    """AI Daily 发布请求"""

    pack_type: str = "daily_pack"  # "analysis_pack" | "daily_pack"
    topic_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    images: List[str] = Field(default_factory=list)  # data URL / 本地路径 / HTTP URL
    tags: List[str] = Field(default_factory=list)
    card_types: List[str] = Field(default_factory=lambda: ["title", "hot-topic"])
    auto_generate_cards: bool = True


class AiDailyRankingCardsRequest(BaseModel):
    """AI Daily 整榜卡片包请求"""

    limit: int = 10
    title: Optional[str] = None
    card_types: List[str] = Field(default_factory=lambda: ["title", "daily-rank"])


class AiDailyRankingPublishRequest(BaseModel):
    """AI Daily 整榜发布请求"""

    limit: int = 10
    title: Optional[str] = None
    content: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    card_types: List[str] = Field(default_factory=lambda: ["title", "daily-rank"])


# Resolve forward refs for EvidenceItem -> SourceItem
EvidenceItem.model_rebuild()
