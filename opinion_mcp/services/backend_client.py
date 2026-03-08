"""
后端 API 客户端

封装对 FastAPI 后端的 HTTP 调用，包括：
- /api/analyze (SSE 流式)
- /api/workflow/status
- /api/xhs/publish
"""

import json
from typing import Any, AsyncGenerator, Dict, List, Optional
from datetime import datetime

import httpx
from loguru import logger

from opinion_mcp.config import config


class BackendClient:
    """后端 API 客户端"""
    
    def __init__(self, base_url: Optional[str] = None):
        """初始化客户端
        
        Args:
            base_url: 后端服务地址，默认使用配置中的 BACKEND_URL
        """
        self.base_url = (base_url or config.BACKEND_URL).rstrip("/")
        logger.info(f"[BackendClient] 初始化，后端地址: {self.base_url}")
    
    # ============================================================
    # 2.2 调用 /api/analyze (SSE 流式)
    # ============================================================
    
    async def call_analyze_api(
        self,
        topic: str,
        source_groups: Optional[List[str]] = None,
        source_names: Optional[List[str]] = None,
        depth: str = "standard",
        debate_rounds: Optional[int] = None,
        image_count: int = 0,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """调用后端分析 API (SSE 流式)
        
        Args:
            topic: 要分析的 AI 话题
            source_groups: 来源组列表
            source_names: 指定来源列表
            depth: 分析深度
            debate_rounds: 辩论轮数
            image_count: AI 配图数量，默认 0
            
        Yields:
            SSE 事件数据
        """
        url = f"{self.base_url}/api/analyze"
        
        # 构建请求体
        payload = {
            "topic": topic,
            "depth": depth,
            "image_count": image_count,
        }
        if source_groups:
            payload["source_groups"] = source_groups
        if source_names:
            payload["source_names"] = source_names
        if debate_rounds is not None:
            payload["debate_rounds"] = debate_rounds
        
        logger.info(f"[BackendClient] 调用分析 API: topic={topic}, depth={depth}")
        
        try:
            # 使用无超时的客户端，因为分析可能需要很长时间
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"[BackendClient] 分析 API 返回错误: {response.status_code} - {error_text}")
                        yield {
                            "agent_name": "System",
                            "step_content": f"API 错误: {response.status_code}",
                            "status": "error"
                        }
                        return
                    
                    # 解析 SSE 流
                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        
                        # SSE 格式: "data: {...}"
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                logger.debug(f"[BackendClient] SSE 事件: {data.get('agent_name')} - {data.get('status')}")
                                yield data
                            except json.JSONDecodeError as e:
                                logger.warning(f"[BackendClient] SSE JSON 解析失败: {e}, line={line}")
                                continue
                        
        except httpx.ConnectError as e:
            logger.error(f"[BackendClient] 连接后端失败: {e}")
            yield {
                "agent_name": "System",
                "step_content": f"无法连接后端服务: {self.base_url}",
                "status": "error"
            }
        except Exception as e:
            logger.exception(f"[BackendClient] 分析 API 调用异常: {e}")
            yield {
                "agent_name": "System",
                "step_content": f"分析过程出错: {str(e)}",
                "status": "error"
            }
    
    # ============================================================
    # 2.3 调用 /api/workflow/status
    # ============================================================
    
    async def get_workflow_status(self) -> Dict[str, Any]:
        """获取当前工作流状态
        
        Returns:
            工作流状态信息，包含:
            - running: bool - 是否正在运行
            - current_step: str - 当前步骤
            - topic: str - 当前话题
            - started_at: str - 开始时间
            - progress: int - 进度百分比
        """
        url = f"{self.base_url}/api/workflow/status"
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                
                if response.status_code != 200:
                    logger.error(f"[BackendClient] 获取工作流状态失败: {response.status_code}")
                    return {
                        "success": False,
                        "running": False,
                        "error": f"API 返回 {response.status_code}"
                    }
                
                data = response.json()
                logger.debug(f"[BackendClient] 工作流状态: running={data.get('running')}, step={data.get('current_step')}")
                return {
                    "success": True,
                    **data
                }
                
        except httpx.ConnectError as e:
            logger.error(f"[BackendClient] 连接后端失败: {e}")
            return {
                "success": False,
                "running": False,
                "error": f"无法连接后端服务: {self.base_url}"
            }
        except Exception as e:
            logger.exception(f"[BackendClient] 获取工作流状态异常: {e}")
            return {
                "success": False,
                "running": False,
                "error": str(e)
            }
    
    # ============================================================
    # 2.4 调用 /api/xhs/publish
    # ============================================================
    
    async def publish_xhs(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """发布内容到小红书
        
        Args:
            title: 标题
            content: 正文内容
            images: 图片列表（本地路径或 HTTP URL）
            tags: 话题标签列表（不含#前缀）
            
        Returns:
            发布结果，包含:
            - success: bool
            - message: str
            - data: Optional[Dict] - 发布成功时的额外数据
        """
        url = f"{self.base_url}/api/xhs/publish"
        
        payload = {
            "title": title,
            "content": content,
            "images": images,
            "tags": tags or []
        }
        
        logger.info(f"[BackendClient] 发布到小红书: title={title[:20]}..., images={len(images)}张")
        
        try:
            async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                data = response.json()
                
                if response.status_code != 200:
                    logger.error(f"[BackendClient] 小红书发布失败: {response.status_code} - {data}")
                    return {
                        "success": False,
                        "message": data.get("message") or f"API 返回 {response.status_code}",
                        "data": None
                    }
                
                logger.info(f"[BackendClient] 小红书发布结果: success={data.get('success')}")
                return data
                
        except httpx.ConnectError as e:
            logger.error(f"[BackendClient] 连接后端失败: {e}")
            return {
                "success": False,
                "message": f"无法连接后端服务: {self.base_url}",
                "data": None
            }
        except Exception as e:
            logger.exception(f"[BackendClient] 小红书发布异常: {e}")
            return {
                "success": False,
                "message": str(e),
                "data": None
            }
    
    # ============================================================
    # 健康检查
    # ============================================================
    
    async def health_check(self) -> bool:
        """检查后端服务是否可用
        
        Returns:
            True 如果后端服务可用，否则 False
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/workflow/status")
                return response.status_code == 200
        except Exception:
            return False


# 导出单例实例
backend_client = BackendClient()
