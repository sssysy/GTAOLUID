import asyncio
import hashlib
from typing import List, Union, Sequence, overload
from pathlib import Path

import httpx

from gsuid_core.logger import logger
from gsuid_core.data_store import get_res_path

CACHE_DIR: Path = get_res_path("GTAOLUID") / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".svg",
    ".ttf",
    ".otf",
    ".woff",
    ".woff2",
}


def get_cache_path(url: str, save_dir: Path | str | None = None) -> Path:
    """按 md5(url) + 原始后缀映射本地缓存路径；非法后缀统一回落 .jpg。"""
    target_dir = Path(save_dir) if save_dir is not None else CACHE_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    clean_url = url.split("?")[0].split("#")[0]
    ext = Path(clean_url).suffix.lower()
    if ext not in _VALID_EXTENSIONS:
        ext = ".jpg"

    stem = hashlib.md5(url.encode("utf-8")).hexdigest()
    return target_dir / f"{stem}{ext}"


async def _download_single(
    client: httpx.AsyncClient,
    url: str,
    target_path: Path,
    force: bool = False,
) -> Path | None:
    """下载单个文件到指定路径；失败返回 None。"""
    if not url or not url.strip():
        return None

    if not force and target_path.is_file() and target_path.stat().st_size > 0:
        return target_path

    target_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        resp = await client.get(url, follow_redirects=True)
        resp.raise_for_status()
        content = resp.content
        if not content:
            logger.warning(f"[GTAOnline · 资源下载] 内容为空: {url}")
            return None
        target_path.write_bytes(content)
        return target_path
    except httpx.HTTPStatusError as e:
        logger.warning(f"[GTAOnline · 资源下载] HTTP {e.response.status_code}: {url}")
        return None
    except httpx.TimeoutException:
        logger.warning(f"[GTAOnline · 资源下载] 超时: {url}")
        return None
    except httpx.HTTPError as e:
        logger.warning(f"[GTAOnline · 资源下载] 请求失败: {url}, 错误: {e!r}")
        return None


@overload
async def download(
    target: str,
    save_dir: Path | str | None = None,
    *,
    save_path: Path | str | None = None,
    max_concurrency: int = 5,
    timeout: float = 30.0,
    force: bool = False,
) -> Path | None: ...


@overload
async def download(
    target: Sequence[str],
    save_dir: Path | str | None = None,
    *,
    save_path: None = None,
    max_concurrency: int = 5,
    timeout: float = 30.0,
    force: bool = False,
) -> List[Path | None]: ...


async def download(
    target: Union[str, Sequence[str]],
    save_dir: Path | str | None = None,
    *,
    save_path: Path | str | None = None,
    max_concurrency: int = 5,
    timeout: float = 30.0,
    force: bool = False,
) -> Union[Path, None, List[Union[Path, None]]]:
    """统一资源下载入口，支持单 URL / 批量并发，自动判定本地缓存。

    Args:
        target: 单个 URL 或 URL 序列
        save_dir: 缓存目录，默认 CACHE_DIR
        save_path: 单 URL 时指定完整落盘路径，覆盖缓存命名
        max_concurrency: 批量下载最大并发数
        timeout: 单请求超时秒数
        force: 为 True 时忽略缓存强制重下

    Returns:
        单 URL 返回 Path | None；序列返回对齐的 Path | None 列表
    """
    if isinstance(target, str):
        url = target.strip()
        if not url:
            return None

        dest_path = Path(save_path) if save_path is not None else get_cache_path(url, save_dir=save_dir)

        if not force and dest_path.is_file() and dest_path.stat().st_size > 0:
            return dest_path

        async with httpx.AsyncClient(timeout=timeout) as client:
            return await _download_single(client, url, dest_path, force=force)

    urls = list(target)
    if not urls:
        return []

    results: List[Path | None] = [None] * len(urls)
    sem = asyncio.Semaphore(max_concurrency)

    async def _worker(client: httpx.AsyncClient, index: int, u: str) -> None:
        if not u or not u.strip():
            results[index] = None
            return

        dest = get_cache_path(u.strip(), save_dir=save_dir)
        if not force and dest.is_file() and dest.stat().st_size > 0:
            results[index] = dest
            return

        async with sem:
            # 并发下二次查缓存，避免同 URL 重复写盘
            if not force and dest.is_file() and dest.stat().st_size > 0:
                results[index] = dest
                return
            results[index] = await _download_single(client, u.strip(), dest, force=force)

    async with httpx.AsyncClient(timeout=timeout) as client:
        await asyncio.gather(*[_worker(client, i, u) for i, u in enumerate(urls)])

    return results
