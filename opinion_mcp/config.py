"""
AIInSight MCP Server 配置

包含服务器配置、后端连接配置、超时设置等。
"""

import os


class Config:
    """MCP 服务器配置"""

    # 渲染服务配置
    RENDERER_SERVICE_URL: str = os.getenv("RENDERER_SERVICE_URL", "http://renderer:3001")

    # MCP 服务器配置
    MCP_PORT: int = int(os.getenv("OPINION_MCP_PORT", "18061"))
    MCP_HOST: str = os.getenv("OPINION_MCP_HOST", "localhost")
    XHS_MCP_URL: str = os.getenv("XHS_MCP_URL", "http://xhs-mcp:18060/mcp")
    REQUIRE_API_KEY: bool = os.getenv("OPINION_REQUIRE_API_KEY", "false").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    API_KEY_REGISTRY_PATH: str = os.getenv(
        "OPINION_API_KEY_REGISTRY_PATH", "cache/api_keys.json"
    )
    ADMIN_TOKEN: str = os.getenv("OPINION_ADMIN_TOKEN", "")

    # 请求超时配置 (秒)
    REQUEST_TIMEOUT: int = int(os.getenv("OPINION_REQUEST_TIMEOUT", "300"))


# 导出配置实例
config = Config()
