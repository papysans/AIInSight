"""
小红书 MCP 发布服务

通过 HTTP 调用 xiaohongshu-mcp 服务发布内容到小红书。
MCP 服务地址：https://github.com/xpzouying/xiaohongshu-mcp
"""

import asyncio
import base64
import httpx
import json
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from zoneinfo import ZoneInfo
from loguru import logger


def _process_image(image: str) -> str:
    """
    处理图片路径/URL/Base64 数据

    - 如果是 Base64 data URL，保存到两容器共享卷并返回 xhs-mcp 侧路径
    - 如果是普通 URL 或本地路径，直接返回
    """
    if image.startswith("data:image/"):
        try:
            # Parse data URL: data:image/png;base64,xxxxx
            header, data = image.split(",", 1)
            # Extract extension from header
            ext = "png"
            if "image/jpeg" in header or "image/jpg" in header:
                ext = "jpg"
            elif "image/png" in header:
                ext = "png"
            elif "image/gif" in header:
                ext = "gif"
            elif "image/webp" in header:
                ext = "webp"

            # Decode and save to shared volume so xhs-mcp can read it
            image_data = base64.b64decode(data)
            filename = f"xhs_upload_{id(image_data)}_{int(os.times().elapsed * 1000) % 1000000}.{ext}"

            api_dir = os.getenv("XHS_IMAGE_API_DIR", "").strip()
            mcp_dir = os.getenv("XHS_IMAGE_MCP_DIR", "").strip()

            if api_dir and mcp_dir:
                os.makedirs(api_dir, exist_ok=True)
                api_path = os.path.join(api_dir, filename)
                mcp_path = os.path.join(mcp_dir, filename)
                with open(api_path, "wb") as f:
                    f.write(image_data)
                logger.info(
                    f"[XHS] Saved image to shared vol: {api_path} → mcp sees: {mcp_path}"
                )
                return mcp_path
            else:
                # Fallback: local /tmp (only works outside Docker)
                temp_path = os.path.join(
                    tempfile.gettempdir(), f"xhs_upload_{id(image)}.{ext}"
                )
                with open(temp_path, "wb") as f:
                    f.write(image_data)
                logger.warning(
                    f"[XHS] XHS_IMAGE_API_DIR not set, saved to tmp (won't work cross-container): {temp_path}"
                )
                return temp_path
        except Exception as e:
            logger.error(f"[XHS] Failed to process Base64 image: {e}")
            return image  # Return original on error
    return image


class XiaohongshuPublisher:
    """小红书 MCP 发布客户端"""

    def __init__(self, mcp_url: Optional[str] = None):
        # Resolve the MCP endpoint at instantiation time so compose/env overrides
        # such as the Docker sidecar URL are honored by the shared singleton.
        self.mcp_url = mcp_url or os.getenv("XHS_MCP_URL", "http://xhs-mcp:18060/mcp")
        self._request_id = 0
        self._login_qrcode_lock = asyncio.Lock()

    def _next_request_id(self) -> int:
        """生成下一个请求 ID"""
        self._request_id += 1
        return self._request_id

    def _get_login_qrcode_dir(self) -> Path:
        """返回登录二维码输出目录，并确保目录存在。"""
        output_dir = Path(os.getenv("XHS_LOGIN_QRCODE_DIR", "outputs/xhs_login"))
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir.resolve()

    def _get_login_qrcode_meta_path(self) -> Path:
        return self._get_login_qrcode_dir() / "latest.json"

    @staticmethod
    def _get_app_timezone() -> ZoneInfo:
        tz_name = os.getenv("TZ", "Asia/Shanghai").strip() or "Asia/Shanghai"
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return ZoneInfo("Asia/Shanghai")

    @staticmethod
    def _get_mcp_source_timezone() -> ZoneInfo:
        tz_name = os.getenv("XHS_MCP_SOURCE_TIMEZONE", "UTC").strip() or "UTC"
        try:
            return ZoneInfo(tz_name)
        except Exception:
            return ZoneInfo("UTC")

    @staticmethod
    def _parse_iso_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=XiaohongshuPublisher._get_app_timezone())
            return parsed
        except ValueError:
            return None

    def _get_login_qrcode_timeout(self) -> float:
        raw = os.getenv("XHS_LOGIN_QRCODE_TIMEOUT_SECONDS", "60").strip()
        try:
            timeout = float(raw)
        except ValueError:
            timeout = 60.0
        return max(5.0, timeout)

    def _load_cached_login_qrcode(self) -> Optional[Dict[str, Any]]:
        output_dir = self._get_login_qrcode_dir()
        meta_path = self._get_login_qrcode_meta_path()
        meta: Dict[str, Any] = {}

        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.debug(f"[XHS MCP] Failed to parse QR metadata: {exc}")

        qr_filename = str(meta.get("qr_filename") or "").strip()
        qr_file: Optional[Path] = None

        if qr_filename:
            candidate = (output_dir / qr_filename).resolve()
            if candidate.parent == output_dir and candidate.is_file():
                qr_file = candidate

        if qr_file is None:
            candidates = sorted(
                output_dir.glob("xhs-login-qrcode-*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                candidate = candidates[0].resolve()
                if candidate.parent == output_dir and candidate.is_file():
                    qr_file = candidate
                    if not qr_filename:
                        qr_filename = candidate.name

        if qr_file is None:
            return None

        expires_at = self._parse_iso_datetime(meta.get("expires_at"))
        if expires_at is None:
            approx_expiry = datetime.fromtimestamp(
                qr_file.stat().st_mtime,
                tz=self._get_app_timezone(),
            ) + timedelta(minutes=5)
            expires_at = approx_expiry

        if expires_at <= datetime.now(tz=self._get_app_timezone()):
            return None

        # Generate ASCII QR from the cached PNG file
        ascii_qr = self._generate_ascii_qr(qr_file.read_bytes())

        return {
            "success": True,
            "message": meta.get("message") or "请使用小红书 App 扫码登录",
            "qr_filename": qr_filename or qr_file.name,
            "qr_image_path": str(qr_file),
            "qr_ascii": ascii_qr,
            "expires_at": expires_at.isoformat(),
        }

    def _save_login_qrcode_meta(self, payload: Dict[str, Any]) -> None:
        meta_path = self._get_login_qrcode_meta_path()
        meta = {
            "message": payload.get("message", ""),
            "qr_filename": payload.get("qr_filename"),
            "expires_at": payload.get("expires_at"),
            "created_at": datetime.now().isoformat(),
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _extract_text_and_png(content: Any) -> tuple[str, Optional[str]]:
        """从 MCP content 列表中提取说明文本和 PNG Base64。"""
        message = ""
        image_b64: Optional[str] = None

        if isinstance(content, list):
            for part in content:
                if not isinstance(part, dict):
                    continue
                if part.get("type") == "text" and not message:
                    message = part.get("text", "")
                if part.get("type") == "image" and part.get("mimeType") == "image/png":
                    image_b64 = part.get("data")

        return message, image_b64

    @staticmethod
    def _generate_ascii_qr(png_bytes: bytes) -> Optional[str]:
        """从 QR 码 PNG 图片中解码出 URL，再生成终端可扫描的 ASCII 二维码。"""
        try:
            from PIL import Image
            from pyzbar.pyzbar import decode as pyzbar_decode
            import qrcode
            import io

            img = Image.open(io.BytesIO(png_bytes))
            decoded = pyzbar_decode(img)
            if not decoded:
                logger.warning("[XHS QR] pyzbar 未能从 PNG 中解码出 QR 数据")
                return None

            qr_data = decoded[0].data.decode("utf-8")
            logger.info(f"[XHS QR] 解码出 QR 数据: {qr_data[:80]}...")

            qr = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=1,
                border=1,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            # 使用 Unicode half-block 字符生成紧凑的终端 QR 码
            modules = qr.get_matrix()
            lines = []
            # 每两行合并为一行，使用 ▀ ▄ █ 空格 来表示
            for r in range(0, len(modules), 2):
                line = ""
                for c in range(len(modules[0])):
                    top = modules[r][c]
                    bot = modules[r + 1][c] if r + 1 < len(modules) else False
                    if top and bot:
                        line += "█"
                    elif top and not bot:
                        line += "▀"
                    elif not top and bot:
                        line += "▄"
                    else:
                        line += " "
                lines.append(line)

            return "\n".join(lines)

        except ImportError as e:
            logger.warning(f"[XHS QR] ASCII QR 生成依赖缺失: {e}")
            return None
        except Exception as e:
            logger.warning(f"[XHS QR] ASCII QR 生成失败: {e}")
            return None

    @staticmethod
    def _extract_expiry(message: str) -> Optional[str]:
        """从二维码提示文案中提取过期时间。"""
        if not message:
            return None

        match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", message)
        if not match:
            return None

        try:
            dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
            source_dt = dt.replace(
                tzinfo=XiaohongshuPublisher._get_mcp_source_timezone()
            )
            return source_dt.astimezone(
                XiaohongshuPublisher._get_app_timezone()
            ).isoformat()
        except ValueError:
            return None

    async def _call_mcp(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """
        调用 MCP 工具 (使用 HTTP 批处理模式以确保 Session 初始化)

        Args:
            tool_name: MCP 工具名称
            arguments: 工具参数
            timeout: 超时时间（秒）

        Returns:
            MCP 响应结果
        """
        # 1. Initialize Request
        init_id = self._next_request_id()
        init_req = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "xiaohongshu-client", "version": "1.0"},
            },
            "id": init_id,
        }

        # 2. Initialized Notification
        initialized_req = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }

        # 3. Tool Call Request
        call_id = self._next_request_id()
        call_req = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments or {},
            },
            "id": call_id,
        }

        # Batch Payload
        payload = [init_req, initialized_req, call_req]

        logger.info(
            f"[XHS MCP] Calling tool: {tool_name}, batch_mode=True, call_id: {call_id}"
        )

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.mcp_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                results = response.json()

                if not isinstance(results, list):
                    return {
                        "success": False,
                        "error": f"Invalid batch response type: {type(results)}",
                    }

                # Find the result for our tool call
                tool_result = None
                for res in results:
                    if res.get("id") == call_id:
                        tool_result = res
                        break

                if not tool_result:
                    # Check for initialize errors
                    for res in results:
                        if "error" in res:
                            logger.error(
                                f"[XHS MCP] Batch error (id={res.get('id')}): {res['error']}"
                            )
                            return {
                                "success": False,
                                "error": f"MCP Error: {res['error'].get('message', res['error'])}",
                            }
                    return {
                        "success": False,
                        "error": "Tool call response not found in batch",
                    }

                if "error" in tool_result:
                    error = tool_result["error"]
                    logger.error(f"[XHS MCP] Tool Error: {error}")
                    return {
                        "success": False,
                        "error": error.get("message", str(error)),
                        "code": error.get("code"),
                    }

                logger.info(f"[XHS MCP] Tool {tool_name} succeeded")
                return {"success": True, "result": tool_result.get("result")}

        except httpx.ConnectError as e:
            logger.error(f"[XHS MCP] Connection error: {e}")
            return {
                "success": False,
                "error": "无法连接到小红书 MCP 服务，请确保服务已启动",
            }
        except httpx.TimeoutException as e:
            logger.error(f"[XHS MCP] Timeout: {e}")
            return {"success": False, "error": "请求超时，请稍后重试"}
        except Exception as e:
            logger.error(f"[XHS MCP] Unexpected error: {e}")
            return {"success": False, "error": str(e)}

    async def is_available(self) -> bool:
        """
        检查 MCP 服务是否可用
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 仅发送 initialize 请求检查
                request_id = self._next_request_id()
                payload = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "health-check", "version": "1.0"},
                    },
                    "id": request_id,
                }
                response = await client.post(
                    self.mcp_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                return True
        except Exception as e:
            logger.debug(f"[XHS MCP] Service not available: {e}")
            return False

    async def check_login_status(self) -> Dict[str, Any]:
        """
        检查小红书登录状态

        Returns:
            登录状态信息
        """
        # The upstream MCP may take >10s to finish browser-backed status checks
        # in Docker mode, so use a wider timeout to avoid false negatives.
        result = await self._call_mcp("check_login_status", timeout=30.0)

        if result.get("success"):
            # 解析 MCP 返回的登录状态
            mcp_result = result.get("result", {})
            # MCP 返回格式可能是 {"content": [{"type": "text", "text": "..."}]}
            content = mcp_result.get("content", [])
            if content and isinstance(content, list) and len(content) > 0:
                text = content[0].get("text", "")
                is_logged_in = "已登录" in text or "logged in" in text.lower()
                return {
                    "success": True,
                    "logged_in": is_logged_in,
                    "message": text,
                }
            return {
                "success": True,
                "logged_in": False,
                "message": "登录状态检查成功，但未获得明确的已登录信号",
            }

        return {
            "success": False,
            "logged_in": False,
            "message": result.get("error", "登录状态检查失败"),
        }

    async def get_login_qrcode(self) -> Dict[str, Any]:
        """
        获取小红书登录二维码，并保存为本地 PNG 文件。

        Returns:
            包含二维码文件路径、文件名、提示文案和过期时间的字典
        """
        cached = self._load_cached_login_qrcode()
        if cached:
            logger.info("[XHS MCP] Reusing cached login QR code")
            return cached

        async with self._login_qrcode_lock:
            cached = self._load_cached_login_qrcode()
            if cached:
                logger.info("[XHS MCP] Reusing cached login QR code after lock")
                return cached

            result = await self._call_mcp(
                "get_login_qrcode", timeout=self._get_login_qrcode_timeout()
            )

            if not result.get("success"):
                return {
                    "success": False,
                    "message": result.get("error", "获取登录二维码失败"),
                }

            mcp_result = result.get("result", {})
            message, image_b64 = self._extract_text_and_png(mcp_result.get("content"))

            # xhs-mcp returns text-only (no image) when already logged in
            if not image_b64:
                already_logged_in = "已登录" in message or "登录状态" in message
                if already_logged_in:
                    return {
                        "success": True,
                        "already_logged_in": True,
                        "message": message,
                    }
                return {
                    "success": False,
                    "message": message or "未从 MCP 返回结果中提取到二维码图片",
                }

            output_dir = self._get_login_qrcode_dir()
            filename = (
                f"xhs-login-qrcode-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
            )
            output_path = output_dir / filename
            png_bytes = base64.b64decode(image_b64)
            output_path.write_bytes(png_bytes)

            ascii_qr = self._generate_ascii_qr(png_bytes)

            payload = {
                "success": True,
                "message": message or "请使用小红书 App 扫码登录",
                "qr_filename": filename,
                "qr_image_path": str(output_path.resolve()),
                "qr_ascii": ascii_qr,
                "expires_at": self._extract_expiry(message),
            }
            self._save_login_qrcode_meta(payload)
            return payload

    async def _verify_authenticated_content_access(self) -> Dict[str, Any]:
        result = await self._call_mcp("list_feeds", timeout=30.0)
        if not result.get("success"):
            return {
                "success": False,
                "message": result.get("error", "内容访问校验失败"),
            }

        mcp_result = result.get("result", {})
        if mcp_result.get("isError"):
            message, _ = self._extract_text_and_png(mcp_result.get("content"))
            return {
                "success": False,
                "message": message or "内容访问校验失败",
            }

        return {"success": True, "message": "内容访问校验通过"}

    async def publish_content(
        self,
        title: str,
        content: str,
        images: List[str],
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        发布图文内容到小红书

        Args:
            title: 标题
            content: 正文内容
            images: 图片列表（支持本地绝对路径或 HTTP URL）

        Returns:
            发布结果
        """
        if not title or not content:
            return {
                "success": False,
                "error": "标题和内容不能为空",
            }

        if not images:
            return {
                "success": False,
                "error": "至少需要一张图片",
            }

        is_available = await self.is_available()
        if not is_available:
            return {
                "success": False,
                "error": "小红书 MCP 服务未启动或无法连接",
                "login_required": False,
            }

        login_status = await self.check_login_status()
        if not login_status.get("logged_in"):
            login_qrcode = await self.get_login_qrcode()
            message = login_status.get("message") or "小红书当前未登录，请扫码后重试"
            response: Dict[str, Any] = {
                "success": False,
                "error": message,
                "message": message,
                "login_required": True,
            }
            if login_qrcode.get("success"):
                response["login_qrcode"] = login_qrcode
                response["qr_image_path"] = login_qrcode.get("qr_image_path")
                response["qr_filename"] = login_qrcode.get("qr_filename")
                response["expires_at"] = login_qrcode.get("expires_at")
            return response

        # Process images: convert Base64 data URLs to temp files
        processed_images = [_process_image(img) for img in images]

        # Process tags: remove # prefix if present (MCP will add it)
        processed_tags = []
        if tags:
            processed_tags = [tag.lstrip("#") for tag in tags if tag]

        logger.info(
            f"[XHS MCP] Publishing: title='{title[:30]}...', images={len(processed_images)}"
        )
        logger.info(f"[XHS MCP] Tags 详情: 原始={tags}, 处理后={processed_tags}")

        # Build MCP arguments
        mcp_args = {
            "title": title,
            "content": content,
            "images": processed_images,
        }

        # Add tags if provided (XHS MCP handles topic selection via browser automation)
        if processed_tags:
            mcp_args["tags"] = processed_tags

        result = await self._call_mcp(
            "publish_content",
            mcp_args,
            timeout=120.0,  # 发布可能需要较长时间
        )

        if result.get("success"):
            mcp_result = result.get("result", {})
            content_list = mcp_result.get("content", [])
            message = ""
            if (
                content_list
                and isinstance(content_list, list)
                and len(content_list) > 0
            ):
                message = content_list[0].get("text", "")

            return {
                "success": True,
                "message": message or "发布成功",
                "data": mcp_result,
            }

        return {
            "success": False,
            "error": result.get("error", "发布失败"),
        }

    async def get_status(self) -> Dict[str, Any]:
        """
        获取小红书 MCP 服务完整状态

        Returns:
            服务状态信息
        """
        # 检查服务可用性
        is_available = await self.is_available()
        if not is_available:
            return {
                "mcp_available": False,
                "login_status": False,
                "message": "小红书 MCP 服务未启动或无法连接",
            }

        # 检查登录状态
        login_result = await self.check_login_status()
        if login_result.get("logged_in"):
            probe_result = await self._verify_authenticated_content_access()
            if not probe_result.get("success"):
                return {
                    "mcp_available": True,
                    "login_status": False,
                    "message": "登录状态疑似有效，但内容访问校验失败："
                    + probe_result.get("message", "请重新扫码登录"),
                }

        return {
            "mcp_available": True,
            "login_status": login_result.get("logged_in", False),
            "message": login_result.get("message", ""),
        }

    async def reset_login(self) -> Dict[str, Any]:
        result = await self._call_mcp("delete_cookies", timeout=30.0)
        if not result.get("success"):
            return {
                "success": False,
                "message": result.get("error", "重置登录状态失败"),
            }

        mcp_result = result.get("result", {})
        content = mcp_result.get("content", [])
        message = "登录状态已重置，请重新扫码登录"
        if content and isinstance(content, list) and len(content) > 0:
            message = content[0].get("text", message)

        return {
            "success": True,
            "message": message,
        }

    # ============================================================
    # Cookie 注入 (Phase 1)
    # ============================================================

    @staticmethod
    def get_xhs_cookies_path() -> Path:
        """获取 xhs-mcp sidecar 使用的 cookies.json 路径（volume 挂载点）。"""
        return Path(
            os.getenv("XHS_COOKIES_PATH", "runtime/xhs/data/cookies.json")
        ).resolve()

    @staticmethod
    def _parse_raw_cookie_header(raw_header: str) -> list[dict[str, Any]]:
        """将浏览器原始 Cookie header 字符串转为 go-rod NetworkCookie 格式。

        输入格式: "name1=val1; name2=val2; ..."
        """
        # 已知需要 httpOnly 的 cookie 名
        HTTPONLY_NAMES = {
            "web_session",
            "galaxy_creator_session_id",
            "customer-sso-sid",
        }
        cookies = []
        for pair in raw_header.split(";"):
            pair = pair.strip()
            if not pair or "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name:
                continue
            cookies.append(
                {
                    "name": name,
                    "value": value,
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                    "expires": -1,
                    "size": len(name) + len(value),
                    "httpOnly": name in HTTPONLY_NAMES,
                    "secure": True,
                    "session": True,
                    "sameSite": "",
                    "priority": "Medium",
                    "sameParty": False,
                    "sourceScheme": "Secure",
                    "sourcePort": 443,
                }
            )
        return cookies

    @staticmethod
    def _is_raw_cookie_header(text: str) -> bool:
        """判断文本是否是原始 Cookie header 格式（name=val; name=val）。"""
        text = text.strip()
        # 不是 JSON（不以 [ 或 { 开头）
        if text.startswith("[") or text.startswith("{"):
            return False
        # 包含 name=value 对用分号分隔
        return "=" in text and "web_session=" in text

    async def verify_and_save_cookies(self, cookies_data: Any) -> Dict[str, Any]:
        """
        校验 cookies 并写入 xhs-mcp 的 volume 挂载路径，
        然后调用 check_login_status 验证是否生效。

        支持三种输入格式:
        1. go-rod 格式 (list of dicts with name/value/domain)
        2. 原始 Cookie header 字符串 ("name1=val1; name2=val2")
        3. JSON 字符串

        Returns:
            {"success": bool, "message": str, "login_verified": bool}
        """
        # 1. 规范化为 go-rod JSON
        if isinstance(cookies_data, str):
            cookies_data = cookies_data.strip()
            if self._is_raw_cookie_header(cookies_data):
                logger.info(
                    "[XHS] Detected raw cookie header string, converting to go-rod format"
                )
                go_rod_cookies = self._parse_raw_cookie_header(cookies_data)
                if not go_rod_cookies:
                    return {
                        "success": False,
                        "message": "解析 cookie 字符串失败，未找到有效的 name=value 对",
                        "login_verified": False,
                    }
                raw = json.dumps(go_rod_cookies, ensure_ascii=False)
            else:
                raw = cookies_data
        elif isinstance(cookies_data, list):
            raw = json.dumps(cookies_data, ensure_ascii=False)
        elif isinstance(cookies_data, dict):
            raw = json.dumps(cookies_data, ensure_ascii=False)
        else:
            return {
                "success": False,
                "message": "不支持的 cookies 格式",
                "login_verified": False,
            }

        # 2. 基本校验：必须包含 web_session
        if "web_session" not in raw:
            return {
                "success": False,
                "message": "cookies 中未找到 web_session 字段，请确认 cookies 来源",
                "login_verified": False,
            }

        # 3. 写盘
        cookie_path = self.get_xhs_cookies_path()
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            cookie_path.write_text(raw, encoding="utf-8")
            logger.info(f"[XHS] Cookies written to {cookie_path} ({len(raw)} bytes)")
        except OSError as e:
            return {
                "success": False,
                "message": f"写入 cookies 失败: {e}",
                "login_verified": False,
            }

        # 4. 验证（xhs-mcp 会在下次请求时重新加载 cookies）
        login_verified = False
        try:
            status = await self.check_login_status()
            login_verified = status.get("logged_in", False)
        except Exception as exc:
            logger.warning(f"[XHS] Cookie verification call failed (non-fatal): {exc}")

        return {
            "success": True,
            "message": "Cookies 已写入"
            + (
                "，登录验证通过 ✅"
                if login_verified
                else "，但登录验证未通过（xhs-mcp 可能需要重启以加载新 cookies）"
            ),
            "login_verified": login_verified,
        }

    # ============================================================
    # Playwright 登录代理 (Phase 2)
    # ============================================================

    @staticmethod
    def _get_renderer_url() -> str:
        return os.getenv("RENDERER_SERVICE_URL", "http://localhost:3001")

    async def start_playwright_login(self) -> Dict[str, Any]:
        """
        通过 renderer 服务启动 Playwright 登录流程，获取小红书 QR 码。

        Returns:
            {"success": bool, "session_id": str, "qr_image_data": str, "message": str}
        """
        url = f"{self._get_renderer_url()}/login-xhs"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url)
                resp.raise_for_status()
                data = resp.json()
                if data.get("success"):
                    # Save QR image to file for the existing QR serving endpoints
                    image_b64 = data.get("qr_image_data", "")
                    if image_b64:
                        output_dir = self._get_login_qrcode_dir()
                        filename = f"xhs-login-qrcode-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
                        output_path = output_dir / filename
                        output_path.write_bytes(base64.b64decode(image_b64))
                        data["qr_filename"] = filename
                        data["qr_image_path"] = str(output_path.resolve())
                        # set a 4-min expiry
                        expires = datetime.now(tz=self._get_app_timezone()) + timedelta(
                            minutes=4
                        )
                        data["expires_at"] = expires.isoformat()
                        self._save_login_qrcode_meta(data)
                return data
        except httpx.ConnectError:
            return {"success": False, "message": "无法连接 renderer 服务"}
        except Exception as e:
            logger.error(f"[XHS] Playwright login start failed: {e}")
            return {"success": False, "message": str(e)}

    async def poll_playwright_login(self, session_id: str) -> Dict[str, Any]:
        """
        轮询 renderer 的 Playwright 登录状态。

        Returns:
            {"status": "pending"|"logged_in"|"expired", "cookies": [...] if logged_in}
        """
        url = f"{self._get_renderer_url()}/login-xhs/status/{session_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                # Auto-inject cookies if login succeeded
                if data.get("status") == "logged_in" and data.get("cookies"):
                    save_result = await self.verify_and_save_cookies(data["cookies"])
                    data["cookie_injected"] = save_result.get("success", False)
                    data["login_verified"] = save_result.get("login_verified", False)

                return data
        except httpx.ConnectError:
            return {"status": "error", "message": "无法连接 renderer 服务"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# 全局单例
xiaohongshu_publisher = XiaohongshuPublisher()
