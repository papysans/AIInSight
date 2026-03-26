from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import List, Optional, Dict, Any


# --- 小红书发布相关 Schema ---
class XhsPublishRequest(BaseModel):
    """小红书发布请求"""

    title: str
    content: str
    images: List[str] = Field(default_factory=list)
    tags: Optional[List[str]] = None


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

    cookies: Any


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
    login_method: Optional[str] = None
    session_id: Optional[str] = None


class XhsVerificationRequest(BaseModel):
    session_id: str
    code: str


class XhsVerificationResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Card Render Schemas
# ============================================================


class CardRenderRequest(BaseModel):
    """通用卡片渲染请求基类"""

    model_config = ConfigDict(extra="allow")
    card_type: str


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

    timeline: List[Dict[str, Any]]


class TrendCardRenderRequest(BaseModel):
    """趋势图卡渲染请求"""

    stage: str
    growth: int
    curve: List[float]


class DailyRankCardRenderRequest(BaseModel):
    """每日榜单卡渲染请求"""

    date: Optional[str] = None
    topics: List[Dict[str, Any]]
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
