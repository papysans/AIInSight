"""
AIInSight MCP Server - 精简版 MCP 服务器主入口

暴露 6 个工具供 AI 助手调用：
- render_cards: 渲染可视化卡片
- publish_xhs_note: 发布小红书笔记
- check_xhs_status: 检查 XHS 状态
- get_xhs_login_qrcode: 获取登录二维码
- check_xhs_login_session: 轮询扫码状态
- submit_xhs_verification: 提交短信验证码

使用方法:
    python -m opinion_mcp.server --port 18061
"""

import argparse
import asyncio
import inspect
import json
import signal
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from opinion_mcp.config import config
from opinion_mcp.services.api_key_registry import api_key_registry
from opinion_mcp.services.account_context import get_account_id, set_account_id

# 导入 6 个工具函数
from opinion_mcp.tools import (
    render_cards,
    publish_xhs_note,
    check_xhs_status,
    get_xhs_login_qrcode,
    check_xhs_login_session,
    submit_xhs_verification,
)


# ============================================================
# MCP 协议数据模型
# ============================================================


class MCPToolInput(BaseModel):
    """MCP 工具输入参数"""

    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


class MCPTool(BaseModel):
    """MCP 工具定义"""

    name: str
    description: str
    inputSchema: MCPToolInput


class MCPToolsResponse(BaseModel):
    """MCP 工具列表响应"""

    tools: List[MCPTool]


class MCPCallToolRequest(BaseModel):
    """MCP 工具调用请求"""

    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPCallToolResponse(BaseModel):
    """MCP 工具调用响应"""

    content: List[Dict[str, Any]]
    isError: bool = False


class MCPServerInfo(BaseModel):
    """MCP 服务器信息"""

    name: str
    version: str
    protocolVersion: str = "2024-11-05"


class MCPInitializeResponse(BaseModel):
    """MCP 初始化响应"""

    serverInfo: MCPServerInfo
    capabilities: Dict[str, Any]


# ============================================================
# 服务器状态
# ============================================================

_server_started_at: Optional[datetime] = None
_shutdown_event: Optional[asyncio.Event] = None


def _resolve_account_id_from_request(request: Request) -> str:
    api_key = request.headers.get("X-API-Key") or request.headers.get("Authorization")
    if api_key:
        value = api_key.replace("Bearer", "").strip()
        if value:
            resolved = api_key_registry.resolve_account_id(value)
            if resolved:
                return resolved
    forwarded = request.headers.get("X-Account-Id")
    return (forwarded or "").strip() or "_default"


def _validate_or_resolve_account_id(request: Request):
    account_id = _resolve_account_id_from_request(request)
    if config.REQUIRE_API_KEY and account_id == "_default":
        return HTTPException(status_code=401, detail="Missing or invalid API key")
    return account_id


# ============================================================
# 初始化 FastAPI 应用
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _server_started_at
    _server_started_at = datetime.now()
    logger.info("AIInSight MCP Server 启动中...")
    yield
    logger.info("AIInSight MCP Server 关闭中...")


app = FastAPI(
    title="AIInSight MCP Server",
    description="AIInSight MCP 服务 - 提供卡片渲染和小红书发布功能",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def inject_account_context(request: Request, call_next):
    resolved = _validate_or_resolve_account_id(request)
    if isinstance(resolved, HTTPException):
        raise resolved
    set_account_id(resolved)
    return await call_next(request)


# ============================================================
# 6 个 MCP 工具定义
# ============================================================

MCP_TOOLS: List[MCPTool] = [
    MCPTool(
        name="render_cards",
        description="渲染可视化卡片。支持 title/impact/radar/timeline/daily-rank/hot-topic 等卡片类型。返回 output_path 和 image_url（不返回 base64）。",
        inputSchema=MCPToolInput(
            type="object",
            properties={
                "specs": {
                    "type": "array",
                    "description": "卡片规格列表，每项包含 card_type 和 payload",
                    "items": {
                        "type": "object",
                        "properties": {
                            "card_type": {
                                "type": "string",
                                "description": "卡片类型: title/impact/radar/timeline/daily-rank/hot-topic",
                            },
                            "payload": {
                                "type": "object",
                                "description": "卡片渲染参数",
                            },
                        },
                        "required": ["card_type", "payload"],
                    },
                }
            },
            required=["specs"],
        ),
    ),
    MCPTool(
        name="publish_xhs_note",
        description="发布小红书笔记（接受原始内容，不再接受 job_id）。发布前请先调用 check_xhs_status 确认登录状态。",
        inputSchema=MCPToolInput(
            type="object",
            properties={
                "title": {"type": "string", "description": "笔记标题"},
                "content": {"type": "string", "description": "笔记正文"},
                "images": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "图片路径或 URL 列表（至少一张）",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "话题标签列表（可选）",
                },
            },
            required=["title", "content", "images"],
        ),
    ),
    MCPTool(
        name="check_xhs_status",
        description="检查小红书 MCP 服务可用性和登录状态。返回 mcp_available、login_status 和详细信息。发布前请先调用此工具确认登录状态。",
        inputSchema=MCPToolInput(type="object", properties={}, required=[]),
    ),
    MCPTool(
        name="get_xhs_login_qrcode",
        description="获取小红书登录二维码。返回可供客户端展示或打开的二维码信息；扫码后请再次调用 check_xhs_status 确认登录状态。",
        inputSchema=MCPToolInput(type="object", properties={}, required=[]),
    ),
    MCPTool(
        name="check_xhs_login_session",
        description="轮询小红书扫码登录状态。扫码后调用此工具检查是否需要验证码或已登录成功。",
        inputSchema=MCPToolInput(
            type="object",
            properties={
                "session_id": {
                    "type": "string",
                    "description": "登录会话 ID（从 get_xhs_login_qrcode 返回）",
                },
            },
            required=["session_id"],
        ),
    ),
    MCPTool(
        name="submit_xhs_verification",
        description="提交小红书登录短信验证码。扫码后如果小红书要求短信验证，使用此工具提交验证码完成登录。",
        inputSchema=MCPToolInput(
            type="object",
            properties={
                "session_id": {
                    "type": "string",
                    "description": "登录会话 ID（从 get_xhs_login_qrcode 返回）",
                },
                "code": {
                    "type": "string",
                    "description": "手机收到的短信验证码",
                },
            },
            required=["session_id", "code"],
        ),
    ),
]

# 工具名称到函数的映射
TOOL_HANDLERS = {
    "render_cards": render_cards,
    "publish_xhs_note": publish_xhs_note,
    "check_xhs_status": check_xhs_status,
    "get_xhs_login_qrcode": get_xhs_login_qrcode,
    "check_xhs_login_session": check_xhs_login_session,
    "submit_xhs_verification": submit_xhs_verification,
}


# ============================================================
# MCP 协议端点 - 标准 SSE 传输层
# ============================================================

# 存储 SSE 会话
_sse_sessions: Dict[str, asyncio.Queue[Dict[str, Any]]] = {}


def _filter_tool_arguments(
    tool_name: str, handler: Any, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """仅保留工具函数签名里声明过的参数，忽略客户端附带的保留字段。"""
    if not arguments:
        return {}

    signature = inspect.signature(handler)
    accepts_var_kwargs = any(
        param.kind == inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    )
    if accepts_var_kwargs:
        return arguments

    allowed = set(signature.parameters.keys())
    filtered = {key: value for key, value in arguments.items() if key in allowed}
    dropped = sorted(key for key in arguments.keys() if key not in allowed)
    if dropped:
        logger.warning(f"[MCP] 工具 {tool_name} 忽略未声明参数: {dropped}")
    return filtered


async def handle_jsonrpc_request(
    request_data: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """处理 JSON-RPC 请求"""
    method = request_data.get("method", "")
    params = request_data.get("params", {})
    request_id = request_data.get("id")

    logger.debug(f"[MCP] JSON-RPC 请求: method={method}, id={request_id}")

    if request_id is None:
        return None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "AIInSight MCP", "version": "2.0.0"},
                "capabilities": {"tools": {"listChanged": False}},
            }
        elif method == "tools/list":
            result = {"tools": [tool.model_dump() for tool in MCP_TOOLS]}
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = dict(params.get("arguments", {}) or {})
            arguments.setdefault("account_id", get_account_id())

            logger.info(f"[MCP] 调用工具: {tool_name}, 参数: {arguments}")

            handler = TOOL_HANDLERS.get(tool_name)
            if not handler:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"未知工具: {tool_name}"},
                }

            filtered_arguments = _filter_tool_arguments(tool_name, handler, arguments)
            tool_result = await handler(**filtered_arguments)
            result_text = json.dumps(tool_result, ensure_ascii=False, indent=2)

            result = {
                "content": [{"type": "text", "text": result_text}],
                "isError": False,
            }
        elif method == "ping":
            result = {}
        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"未知方法: {method}"},
            }

        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    except Exception as e:
        logger.exception(f"[MCP] 处理请求失败: {e}")
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": str(e)},
        }


@app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE 端点 - 标准 MCP 协议传输层"""
    session_id = str(uuid.uuid4())
    queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    _sse_sessions[session_id] = queue

    logger.info(f"[MCP] SSE 连接建立: session={session_id}")

    async def event_generator():
        try:
            endpoint_event = (
                f"event: endpoint\ndata: /message?sessionId={session_id}\n\n"
            )
            yield endpoint_event

            while True:
                try:
                    if await request.is_disconnected():
                        break

                    try:
                        message = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield f"event: message\ndata: {json.dumps(message)}\n\n"
                    except asyncio.TimeoutError:
                        yield ": heartbeat\n\n"

                except asyncio.CancelledError:
                    break

        finally:
            _sse_sessions.pop(session_id, None)
            logger.info(f"[MCP] SSE 连接关闭: session={session_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/message")
async def message_endpoint(request: Request, sessionId: Optional[str] = None):
    """消息端点 - 接收客户端的 JSON-RPC 请求"""
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"[MCP] 解析请求体失败: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    resolved = _validate_or_resolve_account_id(request)
    if isinstance(resolved, HTTPException):
        raise resolved
    account_id = set_account_id(resolved)
    logger.debug(
        f"[MCP] 收到消息: session={sessionId}, account={account_id}, body={body}"
    )

    if isinstance(body, list):
        requests = body
    else:
        requests = [body]

    responses = []
    for req in requests:
        response = await handle_jsonrpc_request(req)
        if response is not None:
            responses.append(response)

    if sessionId and sessionId in _sse_sessions:
        queue = _sse_sessions[sessionId]
        for resp in responses:
            await queue.put(resp)
        return {"status": "accepted"}

    if len(responses) == 1:
        return responses[0]
    return responses


@app.post("/mcp")
async def mcp_post_endpoint(request: Request):
    """MCP POST 端点 - 兼容直接 POST JSON-RPC 请求"""
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"[MCP] 解析请求体失败: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    resolved = _validate_or_resolve_account_id(request)
    if isinstance(resolved, HTTPException):
        raise resolved
    set_account_id(resolved)

    if isinstance(body, list):
        requests = body
    else:
        requests = [body]

    responses = []
    for req in requests:
        response = await handle_jsonrpc_request(req)
        if response is not None:
            responses.append(response)

    if len(responses) == 1:
        return responses[0]
    return responses


@app.get("/mcp")
async def mcp_info():
    """MCP 服务信息端点"""
    return {
        "name": "AIInSight MCP",
        "version": "2.0.0",
        "protocolVersion": "2024-11-05",
        "description": "AIInSight MCP 服务 - 卡片渲染 + 小红书发布",
        "transport": "sse",
        "endpoints": {"sse": "/sse", "message": "/message"},
    }


@app.get("/")
async def root_get():
    """根路径 GET - 返回服务信息"""
    return {
        "name": "AIInSight MCP",
        "version": "2.0.0",
        "protocolVersion": "2024-11-05",
        "description": "AIInSight MCP 服务 - 卡片渲染 + 小红书发布",
        "transport": "sse",
        "endpoints": {"sse": "/sse", "message": "/message", "mcp": "/mcp"},
    }


@app.post("/")
async def root_post(request: Request):
    """根路径 POST - 处理 JSON-RPC 请求（兼容 mcporter）"""
    try:
        body = await request.json()
    except Exception as e:
        logger.error(f"[MCP] 解析请求体失败: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    resolved = _validate_or_resolve_account_id(request)
    if isinstance(resolved, HTTPException):
        raise resolved
    set_account_id(resolved)

    if isinstance(body, list):
        requests = body
    else:
        requests = [body]

    responses = []
    for req in requests:
        response = await handle_jsonrpc_request(req)
        if response is not None:
            responses.append(response)

    if len(responses) == 1:
        return responses[0]
    return responses if responses else {"status": "ok"}


@app.post("/mcp/initialize")
async def mcp_initialize() -> MCPInitializeResponse:
    """MCP 初始化端点 (HTTP 模式)"""
    return MCPInitializeResponse(
        serverInfo=MCPServerInfo(
            name="AIInSight MCP", version="2.0.0", protocolVersion="2024-11-05"
        ),
        capabilities={
            "tools": {"listChanged": False},
        },
    )


@app.get("/mcp/tools")
@app.post("/mcp/tools/list")
async def mcp_list_tools() -> MCPToolsResponse:
    """MCP 工具列表端点"""
    return MCPToolsResponse(tools=MCP_TOOLS)


@app.post("/mcp/tools/call")
async def mcp_call_tool(request: MCPCallToolRequest) -> MCPCallToolResponse:
    """MCP 工具调用端点 (HTTP 模式)"""
    tool_name = request.name
    arguments = dict(request.arguments or {})
    arguments.setdefault("account_id", get_account_id())

    logger.info(f"[MCP] 调用工具: {tool_name}, 参数: {arguments}")

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        logger.error(f"[MCP] 未知工具: {tool_name}")
        return MCPCallToolResponse(
            content=[{"type": "text", "text": f"未知工具: {tool_name}"}], isError=True
        )

    try:
        filtered_arguments = _filter_tool_arguments(tool_name, handler, arguments)
        result = await handler(**filtered_arguments)

        result_text = json.dumps(result, ensure_ascii=False, indent=2)
        logger.info(f"[MCP] 工具 {tool_name} 执行成功")

        return MCPCallToolResponse(
            content=[{"type": "text", "text": result_text}], isError=False
        )

    except Exception as e:
        logger.exception(f"[MCP] 工具 {tool_name} 执行失败: {e}")
        return MCPCallToolResponse(
            content=[{"type": "text", "text": f"工具执行失败: {str(e)}"}], isError=True
        )


# ============================================================
# 健康检查端点
# ============================================================


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康检查端点"""
    uptime_seconds = None
    if _server_started_at:
        uptime_seconds = (datetime.now() - _server_started_at).total_seconds()

    return {
        "status": "healthy",
        "service": "AIInSight MCP Server",
        "version": "2.0.0",
        "started_at": _server_started_at.isoformat() if _server_started_at else None,
        "uptime_seconds": round(uptime_seconds, 2) if uptime_seconds else None,
        "available_tools": [tool.name for tool in MCP_TOOLS],
        "backend_url": config.BACKEND_URL,
    }


@app.get("/readiness")
async def readiness_check() -> Dict[str, Any]:
    return {
        "status": "ready",
        "service": "AIInSight MCP Server",
        "available_tools": [tool.name for tool in MCP_TOOLS],
        "backend_url": config.BACKEND_URL,
        "require_api_key": config.REQUIRE_API_KEY,
    }


# ============================================================
# Admin API Keys 管理
# ============================================================


class ApiKeyCreateRequest(BaseModel):
    account_id: str
    note: str = ""


class ApiKeyRevokeRequest(BaseModel):
    api_key: str


@app.post("/admin/api-keys")
async def create_api_key(body: ApiKeyCreateRequest) -> Dict[str, Any]:
    logger.info(f"[ADMIN] Create API key for account={body.account_id}")
    return api_key_registry.create_key(account_id=body.account_id, note=body.note)


@app.get("/admin/api-keys")
async def list_api_keys() -> Dict[str, Any]:
    logger.info("[ADMIN] List API keys")
    return {"success": True, "keys": api_key_registry.list_keys()}


@app.post("/admin/api-keys/revoke")
async def revoke_api_key(body: ApiKeyRevokeRequest) -> Dict[str, Any]:
    logger.info("[ADMIN] Revoke API key")
    revoked = api_key_registry.revoke_key(body.api_key)
    return {
        "success": revoked,
        "revoked": revoked,
    }


# XHS 二维码便捷端点（保留兼容性）
@app.post("/get_xhs_login_qrcode")
@app.get("/get_xhs_login_qrcode")
async def direct_get_xhs_login_qrcode() -> Dict[str, Any]:
    """直接获取小红书登录二维码"""
    return await get_xhs_login_qrcode()


# ============================================================
# 命令行参数解析与主入口
# ============================================================


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AIInSight MCP Server - 卡片渲染 + 小红书发布 MCP 服务",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=config.MCP_PORT,
        help=f"服务器端口 (默认: {config.MCP_PORT})",
    )

    parser.add_argument(
        "--host",
        type=str,
        default=config.MCP_HOST,
        help=f"服务器主机 (默认: {config.MCP_HOST})",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式",
    )

    return parser.parse_args()


def setup_signal_handlers() -> None:
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info(f"收到信号 {sig_name}，正在优雅关闭...")
        if _shutdown_event:
            _shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGTERM, signal_handler)


def log_startup_info(host: str, port: int) -> None:
    tools = [tool.name for tool in MCP_TOOLS]
    logger.info("=" * 60)
    logger.info("AIInSight MCP Server 启动")
    logger.info("=" * 60)
    logger.info(f"  服务地址: http://{host}:{port}")
    logger.info(f"  健康检查: http://{host}:{port}/health")
    logger.info(f"  MCP 端点: http://{host}:{port}/mcp")
    logger.info(f"  后端地址: {config.BACKEND_URL}")
    logger.info(f"  可用工具: {len(tools)} 个")
    for tool in tools:
        logger.info(f"    - {tool}")
    logger.info("=" * 60)


def main() -> None:
    args = parse_args()

    if args.debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    setup_signal_handlers()
    log_startup_info(args.host, args.port)

    try:
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="debug" if args.debug else "info",
        )

    except KeyboardInterrupt:
        logger.info("收到键盘中断，正在关闭...")
    except Exception as e:
        logger.exception(f"服务器运行出错: {e}")
        sys.exit(1)
    finally:
        logger.info("服务器已关闭")


if __name__ == "__main__":
    main()
