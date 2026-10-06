"""sc-cache 玩家名称转 Rockstar ID 查询。"""

from typing import Any, Optional
from urllib.parse import quote

import httpx

from gsuid_core.logger import logger

SC_CACHE_BASE_URL = "https://sc-cache.com"
TIMEOUT = httpx.Timeout(15.0)

HEADERS = {
    "User-Agent": "GTAOLUID/0.1.0 (gsuid_core)",
}


def _parse_rid(value: Any) -> Optional[int]:
    """严格解析 RID：仅接受正整数或纯数字字符串，其余回退 None。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            rid = int(text)
            return rid if rid > 0 else None
    return None


async def name_to_rid(name: str) -> Optional[int]:
    """按玩家名称查询 Rockstar ID；未命中或请求失败回退 None。

    sc-cache 为第三方缓存数据库，数据可能过期，未命中由调用方决定后续回退。
    """
    target = (name or "").strip()
    if not target:
        return None

    url = f"{SC_CACHE_BASE_URL}/n/{quote(target, safe='')}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
            resp = await client.get(url)
    except httpx.HTTPError as e:
        logger.warning(f"[GTAOnline · 名称转换] sc-cache 请求失败 [{target}]: {e!r}")
        return None

    if resp.status_code != 200:
        logger.info(f"[GTAOnline · 名称转换] sc-cache 未命中 [{target}] [HTTP {resp.status_code}]")
        return None

    try:
        data = resp.json()
    except ValueError:
        logger.warning(f"[GTAOnline · 名称转换] sc-cache 响应解析失败 [{target}]")
        return None

    if not isinstance(data, dict):
        return None
    return _parse_rid(data.get("id"))
