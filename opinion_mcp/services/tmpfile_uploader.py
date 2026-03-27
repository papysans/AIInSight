"""tmpfile.link 上传工具"""
from typing import Optional
import httpx
from loguru import logger


async def upload_to_tmpfile(file_path: str) -> Optional[str]:
    """上传文件到 tmpfile.link，返回下载链接

    Args:
        file_path: 本地文件路径

    Returns:
        下载链接，失败返回 None
    """
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            with open(file_path, "rb") as f:
                files = {"file": f}
                resp = await client.post("https://tmpfile.link/api/upload", files=files)
                resp.raise_for_status()
                data = resp.json()
                return data.get("downloadLink")
    except Exception as e:
        logger.warning(f"[tmpfile_uploader] 上传失败: {e}")
        return None
