"""
MCP Tools - AI 话题分析工具集

包含以下工具:
- analyze_topic: 启动 AI 话题分析任务
- get_analysis_status: 查询分析进度
- get_analysis_result: 获取分析结果
- update_copywriting: 修改文案
- publish_to_xhs: 发布到小红书
- get_settings: 获取配置
- register_webhook: 注册进度推送
- get_ai_daily: 获取 AI 日报
- analyze_ai_topic: 深度分析 AI 话题
- generate_ai_daily_cards: 生成 AI 日报卡片
"""

# 分析相关工具
from opinion_mcp.tools.analyze import (
    analyze_topic,
    retrieve_and_report,
    submit_analysis_result,
    get_analysis_status,
    get_analysis_result,
    update_copywriting,
    generate_topic_cards,
)

# 发布工具
from opinion_mcp.tools.publish import (
    check_xhs_status,
    xhs_login,
    get_xhs_login_qrcode,
    reset_xhs_login,
    submit_xhs_verification,
    check_xhs_login_session,
    upload_xhs_cookies,
    get_xhs_login_qrcode_v2,
    poll_xhs_login_v2,
    publish_to_xhs,
)

# 发布预检工具
from opinion_mcp.tools.validate_publish import validate_publish

# 设置和 Webhook 工具
from opinion_mcp.tools.settings import (
    get_settings,
    register_webhook,
)

# AI 日报工具
from opinion_mcp.tools.ai_daily import (
    get_ai_daily,
    analyze_ai_topic,
    generate_ai_daily_cards,
    publish_ai_daily,
    generate_ai_daily_ranking_cards,
    publish_ai_daily_ranking,
)

__all__ = [
    # 分析相关
    "analyze_topic",
    "retrieve_and_report",
    "submit_analysis_result",
    "get_analysis_status",
    "get_analysis_result",
    "update_copywriting",
    "generate_topic_cards",
    # 发布
    "check_xhs_status",
    "xhs_login",
    "get_xhs_login_qrcode",
    "reset_xhs_login",
    "submit_xhs_verification",
    "check_xhs_login_session",
    "upload_xhs_cookies",
    "get_xhs_login_qrcode_v2",
    "poll_xhs_login_v2",
    "publish_to_xhs",
    # 发布预检
    "validate_publish",
    # 设置和 Webhook
    "get_settings",
    "register_webhook",
    # AI 日报
    "get_ai_daily",
    "analyze_ai_topic",
    "generate_ai_daily_cards",
    "publish_ai_daily",
    "generate_ai_daily_ranking_cards",
    "publish_ai_daily_ranking",
]
