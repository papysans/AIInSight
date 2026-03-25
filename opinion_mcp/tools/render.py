"""MCP 渲染工具 - 调用 card_render_client 渲染卡片"""
from typing import Any, Dict, List
from loguru import logger


async def render_cards(specs: List[Dict[str, Any]], account_id: str = None) -> Dict[str, Any]:
    """渲染可视化卡片

    Args:
        specs: 卡片规格列表，每项包含 card_type 和 payload

    Returns:
        { "results": [{ "success": bool, "output_path": str, "image_url": str }] }
    """
    from app.services.card_render_client import card_render_client

    results = []
    for spec in specs:
        card_type = spec.get("card_type", "")
        payload = spec.get("payload", {})

        try:
            result = await card_render_client.render(card_type, payload)
            # 只返回 output_path 和 image_url，不返回 base64
            results.append({
                "success": result.get("success", False),
                "output_path": result.get("output_path"),
                "image_url": result.get("image_url"),
                "card_type": card_type,
            })
        except Exception as e:
            logger.error(f"[render_cards] {card_type} 渲染失败: {e}")
            results.append({
                "success": False,
                "output_path": None,
                "image_url": None,
                "card_type": card_type,
                "error": str(e),
            })

    return {"results": results}
