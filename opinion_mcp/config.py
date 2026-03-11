"""
AIInSight MCP Server 配置

包含服务器配置、后端连接配置、超时设置等。
"""

import os
from typing import List, Dict


class Config:
    """MCP 服务器配置"""

    # 后端服务配置
    BACKEND_URL: str = os.getenv("OPINION_BACKEND_URL", "http://localhost:8000")

    # MCP 服务器配置
    MCP_PORT: int = int(os.getenv("OPINION_MCP_PORT", "18061"))
    MCP_HOST: str = os.getenv("OPINION_MCP_HOST", "localhost")
    XHS_MCP_URL: str = os.getenv("XHS_MCP_URL", "http://xhs-mcp:18060/mcp")

    # 请求超时配置 (秒)
    REQUEST_TIMEOUT: int = int(os.getenv("OPINION_REQUEST_TIMEOUT", "300"))
    AI_DAILY_ANALYZE_TIMEOUT: int = int(
        os.getenv("OPINION_AI_DAILY_ANALYZE_TIMEOUT", "900")
    )

    # Webhook 配置
    WEBHOOK_RETRY_COUNT: int = int(os.getenv("OPINION_WEBHOOK_RETRY_COUNT", "3"))
    WEBHOOK_RETRY_DELAY: float = float(os.getenv("OPINION_WEBHOOK_RETRY_DELAY", "1.0"))

    # 分析默认配置
    DEFAULT_DEBATE_ROUNDS: int = 2
    DEFAULT_IMAGE_COUNT: int = 0
    MAX_IMAGE_COUNT: int = 9
    MAX_DEBATE_ROUNDS: int = 5

    # 来源组配置
    SOURCE_GROUPS: Dict[str, List[str]] = {
        "media": ["aibase", "jiqizhixin", "qbitai", "techcrunch_ai"],
        "research": ["hf_papers"],
        "code": ["github_trending"],
        "community": ["hn", "reddit"],
    }

    DEFAULT_SOURCE_GROUPS: List[str] = ["media", "research", "code", "community"]

    # 深度预设
    DEPTH_PRESETS: Dict[str, Dict] = {
        "quick": {"debate_rounds": 0, "max_extractions": 5},
        "standard": {"debate_rounds": 2, "max_extractions": 10},
        "deep": {"debate_rounds": 4, "max_extractions": 20},
    }

    # 可用来源列表 (用于 MCP 工具描述)
    AVAILABLE_SOURCES: List[Dict[str, str]] = [
        {"code": "aibase", "name": "AIbase", "emoji": "🤖"},
        {"code": "jiqizhixin", "name": "机器之心", "emoji": "🧠"},
        {"code": "qbitai", "name": "量子位", "emoji": "⚛️"},
        {"code": "techcrunch_ai", "name": "TechCrunch AI", "emoji": "📰"},
        {"code": "hf_papers", "name": "HF Papers", "emoji": "📄"},
        {"code": "github_trending", "name": "GitHub Trending", "emoji": "💻"},
        {"code": "hn", "name": "Hacker News", "emoji": "🔶"},
        {"code": "reddit", "name": "Reddit", "emoji": "🔴"},
    ]

    # 进度步骤映射
    STEP_PROGRESS_MAP: Dict[str, Dict] = {
        "source_retriever": {"name": "证据检索", "progress": 10},
        "reporter": {"name": "事实提炼汇总", "progress": 25},
        "analyst": {"name": "AI 领域分析", "progress": 40},
        "debater": {"name": "多角度辩论", "progress": 60},
        "writer": {"name": "文案生成", "progress": 80},
        "image_generator": {"name": "图片生成", "progress": 95},
        "finished": {"name": "完成", "progress": 100},
    }

    @classmethod
    def get_source_name(cls, code: str) -> str:
        """根据来源代码获取来源名称"""
        for source in cls.AVAILABLE_SOURCES:
            if source["code"] == code:
                return source["name"]
        return code

    @classmethod
    def get_source_emoji(cls, code: str) -> str:
        """根据来源代码获取 emoji"""
        for source in cls.AVAILABLE_SOURCES:
            if source["code"] == code:
                return source["emoji"]
        return "📌"

    @classmethod
    def get_all_source_codes(cls) -> List[str]:
        """获取所有可用来源代码"""
        return [s["code"] for s in cls.AVAILABLE_SOURCES]

    @classmethod
    def validate_sources(cls, sources: List[str]) -> List[str]:
        """验证来源代码列表，返回有效的来源代码"""
        valid_codes = {s["code"] for s in cls.AVAILABLE_SOURCES}
        return [s for s in sources if s in valid_codes]

    @classmethod
    def get_step_info(cls, step: str) -> Dict:
        """获取步骤信息"""
        return cls.STEP_PROGRESS_MAP.get(step, {"name": step, "progress": 0})


# 导出配置实例
config = Config()
