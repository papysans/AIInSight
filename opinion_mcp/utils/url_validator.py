"""
URL 验证工具

提供异步 URL 可访问性验证功能，用于验证图片 URL 是否有效。
支持超时处理、批量验证和图片下载。

Validates: Requirements 1.4, 3.3
"""

import asyncio
import base64
import os
import uuid
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from loguru import logger


# 图片缓存目录
IMAGE_CACHE_DIR = Path("outputs/image_cache")


def _is_data_image_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith("data:image/")


def _is_existing_local_path(value: str) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    if parsed.scheme:
        return False
    return Path(value).expanduser().exists()


@dataclass
class URLValidationResult:
    """URL 验证结果"""
    url: str
    valid: bool
    status_code: Optional[int] = None
    error: Optional[str] = None
    response_time_ms: Optional[int] = None


@dataclass
class ImageDownloadResult:
    """图片下载结果"""
    original_url: str
    local_path: Optional[str] = None
    success: bool = False
    error: Optional[str] = None


async def validate_url(
    url: str,
    timeout: float = 10.0,
    allow_redirects: bool = True,
) -> URLValidationResult:
    """
    验证单个 URL 的可访问性
    
    Property 2: URL Validation Correctness
    For any image URL, the validation function SHALL return `true` if and only if 
    the URL is accessible (HTTP 200 response), and SHALL return `false` for all 
    other cases (4xx, 5xx, timeout, invalid URL format).
    
    Args:
        url: 要验证的 URL
        timeout: 超时时间（秒）
        allow_redirects: 是否允许重定向
        
    Returns:
        URLValidationResult: 验证结果
    """
    # 基本格式验证
    if not url or not isinstance(url, str):
        return URLValidationResult(
            url=url or "",
            valid=False,
            error="URL 为空或格式无效"
        )
    
    url = url.strip()

    if _is_data_image_url(url):
        return URLValidationResult(
            url=url,
            valid=True,
            status_code=200,
            response_time_ms=0,
        )

    if _is_existing_local_path(url):
        return URLValidationResult(
            url=str(Path(url).expanduser().resolve()),
            valid=True,
            status_code=200,
            response_time_ms=0,
        )
    
    # URL 格式检查
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return URLValidationResult(
                url=url,
                valid=False,
                error="URL 格式无效：缺少协议或域名"
            )
        if parsed.scheme not in ("http", "https"):
            return URLValidationResult(
                url=url,
                valid=False,
                error=f"不支持的协议: {parsed.scheme}"
            )
    except Exception as e:
        return URLValidationResult(
            url=url,
            valid=False,
            error=f"URL 解析失败: {str(e)}"
        )
    
    # HTTP 请求验证
    try:
        import time
        start_time = time.time()
        
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=allow_redirects,
        ) as client:
            # 使用 HEAD 请求减少数据传输，如果失败则尝试 GET
            try:
                response = await client.head(url)
            except httpx.HTTPStatusError:
                # 某些服务器不支持 HEAD，尝试 GET
                response = await client.get(url)
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 只有 200 才算有效
            if response.status_code == 200:
                return URLValidationResult(
                    url=url,
                    valid=True,
                    status_code=response.status_code,
                    response_time_ms=response_time_ms,
                )
            else:
                return URLValidationResult(
                    url=url,
                    valid=False,
                    status_code=response.status_code,
                    error=f"HTTP {response.status_code}",
                    response_time_ms=response_time_ms,
                )
                
    except httpx.TimeoutException:
        return URLValidationResult(
            url=url,
            valid=False,
            error="请求超时"
        )
    except httpx.ConnectError as e:
        return URLValidationResult(
            url=url,
            valid=False,
            error=f"连接失败: {str(e)}"
        )
    except Exception as e:
        return URLValidationResult(
            url=url,
            valid=False,
            error=f"验证失败: {str(e)}"
        )


async def validate_urls(
    urls: List[str],
    timeout: float = 10.0,
    concurrency: int = 5,
) -> List[URLValidationResult]:
    """
    批量验证多个 URL
    
    Args:
        urls: URL 列表
        timeout: 每个 URL 的超时时间（秒）
        concurrency: 并发数
        
    Returns:
        List[URLValidationResult]: 验证结果列表（保持原顺序）
    """
    if not urls:
        return []
    
    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(concurrency)
    
    async def validate_with_semaphore(url: str) -> URLValidationResult:
        async with semaphore:
            return await validate_url(url, timeout=timeout)
    
    # 并发验证所有 URL
    tasks = [validate_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    return list(results)


async def filter_valid_urls(
    urls: List[str],
    timeout: float = 10.0,
    concurrency: int = 5,
) -> Tuple[List[str], List[URLValidationResult]]:
    """
    过滤出有效的 URL，保持原顺序
    
    Property 3: Image Filtering Preserves Valid URLs
    For any list of image URLs containing both valid and invalid URLs, 
    the filtering function SHALL return a list containing exactly the valid URLs, 
    preserving their original order.
    
    Args:
        urls: URL 列表
        timeout: 每个 URL 的超时时间（秒）
        concurrency: 并发数
        
    Returns:
        Tuple[List[str], List[URLValidationResult]]: 
            - 有效 URL 列表（保持原顺序）
            - 所有验证结果列表
    """
    if not urls:
        return [], []
    
    # 验证所有 URL
    results = await validate_urls(urls, timeout=timeout, concurrency=concurrency)
    
    # 过滤有效 URL，保持顺序
    valid_urls = [r.url for r in results if r.valid]
    
    # 记录日志
    valid_count = len(valid_urls)
    invalid_count = len(urls) - valid_count
    if invalid_count > 0:
        logger.warning(f"[URL Validator] {invalid_count}/{len(urls)} 个 URL 无效")
        for r in results:
            if not r.valid:
                logger.debug(f"[URL Validator] 无效: {r.url} - {r.error}")
    
    return valid_urls, results



async def download_image(
    url: str,
    timeout: float = 30.0,
    cache_dir: Optional[Path] = None,
) -> ImageDownloadResult:
    """
    下载单个图片到本地
    
    Args:
        url: 图片 URL
        timeout: 超时时间（秒）
        cache_dir: 缓存目录，默认为 outputs/image_cache
        
    Returns:
        ImageDownloadResult: 下载结果
    """
    if not url or not isinstance(url, str):
        return ImageDownloadResult(
            original_url=url or "",
            success=False,
            error="URL 为空或格式无效"
        )
    
    url = url.strip()
    
    # 确保缓存目录存在
    save_dir = cache_dir or IMAGE_CACHE_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    if _is_existing_local_path(url):
        local_path = str(Path(url).expanduser().resolve())
        return ImageDownloadResult(
            original_url=url,
            local_path=local_path,
            success=True,
        )

    if _is_data_image_url(url):
        try:
            header, encoded = url.split(",", 1)
            if ";base64" not in header:
                raise ValueError("仅支持 base64 data URL")

            if "image/png" in header:
                ext = ".png"
            elif "image/webp" in header:
                ext = ".webp"
            elif "image/gif" in header:
                ext = ".gif"
            else:
                ext = ".jpg"

            filename = f"{uuid.uuid4().hex[:12]}{ext}"
            local_path = save_dir / filename
            local_path.write_bytes(base64.b64decode(encoded))
            return ImageDownloadResult(
                original_url=url,
                local_path=str(local_path.resolve()),
                success=True,
            )
        except Exception as e:
            return ImageDownloadResult(
                original_url=url,
                success=False,
                error=f"data URL 解析失败: {str(e)}",
            )
    
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                return ImageDownloadResult(
                    original_url=url,
                    success=False,
                    error=f"HTTP {response.status_code}"
                )
            
            # 确定文件扩展名
            content_type = response.headers.get("content-type", "")
            if "jpeg" in content_type or "jpg" in content_type:
                ext = ".jpg"
            elif "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"
            elif "gif" in content_type:
                ext = ".gif"
            else:
                # 从 URL 推断
                parsed = urlparse(url)
                path_ext = os.path.splitext(parsed.path)[1].lower()
                ext = path_ext if path_ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"] else ".jpg"
            
            # 生成唯一文件名
            filename = f"{uuid.uuid4().hex[:12]}{ext}"
            local_path = save_dir / filename
            
            # 保存文件
            with open(local_path, "wb") as f:
                f.write(response.content)
            
            logger.debug(f"[Image Download] 下载成功: {url} -> {local_path}")
            
            return ImageDownloadResult(
                original_url=url,
                local_path=str(local_path.absolute()),
                success=True,
            )
            
    except httpx.TimeoutException:
        return ImageDownloadResult(
            original_url=url,
            success=False,
            error="下载超时"
        )
    except Exception as e:
        return ImageDownloadResult(
            original_url=url,
            success=False,
            error=f"下载失败: {str(e)}"
        )


async def download_images(
    urls: List[str],
    timeout: float = 30.0,
    concurrency: int = 3,
    cache_dir: Optional[Path] = None,
) -> Tuple[List[str], List[ImageDownloadResult]]:
    """
    批量下载图片到本地
    
    Args:
        urls: 图片 URL 列表
        timeout: 每个图片的超时时间（秒）
        concurrency: 并发数
        cache_dir: 缓存目录
        
    Returns:
        Tuple[List[str], List[ImageDownloadResult]]:
            - 成功下载的本地路径列表（保持原顺序）
            - 所有下载结果列表
    """
    if not urls:
        return [], []
    
    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(concurrency)
    
    async def download_with_semaphore(url: str) -> ImageDownloadResult:
        async with semaphore:
            return await download_image(url, timeout=timeout, cache_dir=cache_dir)
    
    # 并发下载所有图片
    tasks = [download_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks)
    
    # 过滤成功的本地路径，保持顺序
    local_paths = [r.local_path for r in results if r.success and r.local_path]
    
    # 记录日志
    success_count = len(local_paths)
    failed_count = len(urls) - success_count
    if failed_count > 0:
        logger.warning(f"[Image Download] {failed_count}/{len(urls)} 个图片下载失败")
        for r in results:
            if not r.success:
                logger.debug(f"[Image Download] 失败: {r.original_url} - {r.error}")
    else:
        logger.info(f"[Image Download] 全部 {success_count} 个图片下载成功")
    
    return local_paths, list(results)
