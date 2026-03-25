"""
后端 API 客户端

封装对 FastAPI 后端的 HTTP 调用，包括：
- /api/xhs/publish
- /api/xhs/login-qrcode
"""

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from opinion_mcp.config import config


class BackendClient:
    """后端 API 客户端"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or config.BACKEND_URL).rstrip("/")
        logger.info(f"[BackendClient] 初始化，后端地址: {self.base_url}")

    @staticmethod
    def _headers(account_id: Optional[str] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if account_id:
            headers["X-Account-Id"] = account_id
        return headers

    # ============================================================
    # 调用 /api/xhs/publish
    # ============================================================

    async def publish_xhs(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None,
        account_id: Optional[str] = None,
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
            "tags": tags or [],
        }
        if account_id:
            payload["account_id"] = account_id

        logger.info(
            f"[BackendClient] 发布到小红书: title={title[:20]}..., images={len(images)}张"
        )

        try:
            async with httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT) as client:
                response = await client.post(
                    url, json=payload, headers={"Content-Type": "application/json"}
                )

                data = response.json()

                if response.status_code != 200:
                    logger.error(
                        f"[BackendClient] 小红书发布失败: {response.status_code} - {data}"
                    )
                    return {
                        "success": False,
                        "message": data.get("message")
                        or f"API 返回 {response.status_code}",
                        "data": None,
                    }

                logger.info(
                    f"[BackendClient] 小红书发布结果: success={data.get('success')}"
                )
                return data

        except httpx.ConnectError as e:
            logger.error(f"[BackendClient] 连接后端失败: {e}")
            return {
                "success": False,
                "message": f"无法连接后端服务: {self.base_url}",
                "data": None,
            }
        except Exception as e:
            logger.exception(f"[BackendClient] 小红书发布异常: {e}")
            return {"success": False, "message": str(e), "data": None}

    async def get_xhs_status(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        """获取小红书 MCP 服务状态和登录状态。"""
        url = f"{self.base_url}/api/xhs/status"
        params = {"account_id": account_id} if account_id else {}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                data = response.json()

                if response.status_code != 200:
                    return {
                        "success": False,
                        "message": data.get("message")
                        or f"API 返回 {response.status_code}",
                    }

                return {
                    "success": True,
                    "mcp_available": data.get("mcp_available", False),
                    "login_status": data.get("login_status", False),
                    "message": data.get("message", ""),
                }

        except httpx.ConnectError as e:
            return {"success": False, "message": f"无法连接后端服务: {self.base_url}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def get_xhs_login_qrcode(
        self, account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取小红书登录二维码信息。"""
        url = f"{self.base_url}/api/xhs/login-qrcode"
        params = {"account_id": account_id} if account_id else {}

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.get(url, params=params)
                data = response.json()

                if response.status_code != 200:
                    logger.error(
                        f"[BackendClient] 获取小红书登录二维码失败: {response.status_code} - {data}"
                    )
                    return {
                        "success": False,
                        "message": data.get("message")
                        or f"API 返回 {response.status_code}",
                    }

                logger.info("[BackendClient] 获取小红书登录二维码成功")
                return data

        except httpx.ConnectError as e:
            logger.error(f"[BackendClient] 连接后端失败: {e}")
            return {
                "success": False,
                "message": f"无法连接后端服务: {self.base_url}",
            }
        except Exception as e:
            logger.exception(f"[BackendClient] 获取小红书登录二维码异常: {e}")
            return {
                "success": False,
                "message": str(e),
            }

    async def reset_xhs_login(self, account_id: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/xhs/login/reset"
        params = {"account_id": account_id} if account_id else {}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, params=params)
                data = response.json()

                if response.status_code != 200:
                    return {
                        "success": False,
                        "message": data.get("message")
                        or f"API 返回 {response.status_code}",
                    }

                return data
        except httpx.ConnectError:
            return {"success": False, "message": f"无法连接后端服务: {self.base_url}"}
        except Exception as e:
            logger.exception(f"[BackendClient] 重置小红书登录异常: {e}")
            return {"success": False, "message": str(e)}

    async def submit_xhs_verification(
        self,
        session_id: str,
        code: str,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/xhs/submit-verification"
        payload: Dict[str, Any] = {"session_id": session_id, "code": code}
        if account_id:
            payload["account_id"] = account_id
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
                data = response.json()
                if response.status_code != 200:
                    return {
                        "success": False,
                        "message": data.get("message")
                        or f"API 返回 {response.status_code}",
                    }
                return data
        except httpx.ConnectError:
            return {"success": False, "message": f"无法连接后端服务: {self.base_url}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def check_xhs_login_session(
        self, session_id: str, account_id: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/xhs/check-login-session/{session_id}"
        params = {"account_id": account_id} if account_id else {}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, params=params)
                data = response.json()
                if response.status_code != 200:
                    return {
                        "success": False,
                        "message": data.get("message")
                        or f"API 返回 {response.status_code}",
                    }
                return data
        except httpx.ConnectError:
            return {"success": False, "message": f"无法连接后端服务: {self.base_url}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ============================================================
    # Cookie 注入 (Phase 1)
    # ============================================================

    async def upload_xhs_cookies(self, cookies_data: Any) -> Dict[str, Any]:
        """将 cookies 上传到后端，由后端写入 xhs-mcp volume 并验证。"""
        url = f"{self.base_url}/api/xhs/upload-cookies"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json={"cookies": cookies_data},
                    headers={"Content-Type": "application/json"},
                )
                data = response.json()

                if response.status_code != 200:
                    return {
                        "success": False,
                        "message": data.get("message")
                        or f"API 返回 {response.status_code}",
                    }

                return data

        except httpx.ConnectError as e:
            logger.error(f"[BackendClient] 连接后端失败: {e}")
            return {"success": False, "message": f"无法连接后端服务: {self.base_url}"}
        except Exception as e:
            logger.exception(f"[BackendClient] 上传 cookies 异常: {e}")
            return {"success": False, "message": str(e)}

    # ============================================================
    # Playwright 登录代理 (Phase 2)
    # ============================================================

    async def get_xhs_login_qrcode_v2(self) -> Dict[str, Any]:
        """通过 Playwright 代理获取小红书登录二维码。"""
        url = f"{self.base_url}/api/xhs/login-qrcode-v2"

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.get(url)
                data = response.json()

                if response.status_code != 200:
                    return {
                        "success": False,
                        "message": data.get("message")
                        or f"API 返回 {response.status_code}",
                    }

                return data

        except httpx.ConnectError as e:
            return {"success": False, "message": f"无法连接后端服务: {self.base_url}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def poll_xhs_login_v2(self, session_id: str) -> Dict[str, Any]:
        """轮询 Playwright 登录状态。"""
        url = f"{self.base_url}/api/xhs/login-qrcode-v2/status/{session_id}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}

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
