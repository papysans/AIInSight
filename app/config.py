import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- 小红书 MCP 发布设置 ---
    XHS_MCP_CONFIG = {
        "enabled": True,
        "mcp_url": os.getenv("XHS_MCP_URL", "http://xhs-mcp:18060/mcp"),
        "auto_publish": False,
    }

    # --- 图片发布配置 (MCP Image Publishing Pipeline) ---
    IMAGE_PUBLISH_CONFIG = {
        "image_publish_mode": os.getenv("IMAGE_PUBLISH_MODE", "ai_only"),
        "render_service_url": os.getenv(
            "RENDER_SERVICE_URL", "http://localhost:8000/render"
        ),
        "render_timeout": int(os.getenv("RENDER_TIMEOUT", "30")),
        "browser_pool_min": int(os.getenv("BROWSER_POOL_MIN", "2")),
        "browser_pool_max": int(os.getenv("BROWSER_POOL_MAX", "4")),
        "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "render_route": "/render-cards",
    }

    # --- AI Daily Pipeline 配置 ---
    AI_DAILY_CONFIG = {
        "enabled": True,
        "cache_dir": "cache/ai_daily",
        "max_topics": 20,
        "collect_interval_hours": 6,
        "renderer_service_url": os.getenv(
            "RENDERER_SERVICE_URL", "http://127.0.0.1:3001"
        ),
        "renderer_timeout": int(os.getenv("RENDERER_TIMEOUT", "30")),
        "preview_output_dir": os.getenv(
            "CARD_PREVIEW_OUTPUT_DIR", "outputs/card_previews"
        ),
        "sources": {
            "aibase": {
                "enabled": True,
                "url": "https://news.aibase.com/zh/",
                "type": "media",
                "lang": "zh",
            },
            "jiqizhixin": {
                "enabled": True,
                "url": "https://www.jiqizhixin.com/",
                "type": "media",
                "lang": "zh",
            },
            "qbitai": {
                "enabled": True,
                "url": "https://www.qbitai.com/",
                "type": "media",
                "lang": "zh",
            },
            "github_trending": {
                "enabled": True,
                "url": "https://github.com/trending",
                "type": "code",
                "lang": "en",
            },
            "producthunt_ai": {
                "enabled": True,
                "url": "https://www.producthunt.com/topics/artificial-intelligence",
                "type": "product",
                "lang": "en",
            },
            "hf_papers": {
                "enabled": True,
                "url": "https://huggingface.co/papers",
                "type": "research",
                "lang": "en",
            },
            "techcrunch_ai": {
                "enabled": True,
                "url": "https://techcrunch.com/category/artificial-intelligence/",
                "type": "media",
                "lang": "en",
            },
            "hn": {
                "enabled": True,
                "url": "https://news.ycombinator.com/",
                "type": "community",
                "lang": "en",
            },
            "reddit": {
                "enabled": True,
                "url": "https://www.reddit.com/",
                "type": "community",
                "lang": "en",
                "requires_credentials": True,
            },
        },
    }


settings = Config()
