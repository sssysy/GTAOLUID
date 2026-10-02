import asyncio
from typing import Any, Optional

import httpx

from gsuid_core.logger import logger

BASE_URL = "https://api.hqshi.cn"
TIMEOUT = httpx.Timeout(30.0)
POLL_INTERVAL = 5.0
POLL_MAX_TIMES = 24

HEADERS = {
    "content-type": "application/json",
    "User-Agent": "GTAOLUID/0.1.0 (gsuid_core)",
}


class GTAOLApiError(Exception):
    """业务异常，消息可直接呈现给用户。"""


async def _get(path: str, params: dict[str, Any]) -> Any:
    url = f"{BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as client:
        resp = await client.get(url, params=params)
    try:
        return resp.json()
    except ValueError as e:
        raise GTAOLApiError(f"接口返回格式异常 [HTTP {resp.status_code}]") from e


def _require_ok(data: Any, api_name: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise GTAOLApiError(f"{api_name} 响应格式异常")
    code = data.get("code")
    if code != 200:
        message = data.get("message", "未知错误")
        raise GTAOLApiError(f"{api_name} 失败 [code={code}]: {message}")
    return data


async def get_status(nickname: str, limit: int = 50) -> dict[str, Any]:
    """查询玩家基本信息与历史快照记录。"""
    data = await _get("/api/status", {"nickname": nickname, "limit": limit})
    _require_ok(data, "玩家信息查询")
    if not data.get("payload"):
        raise GTAOLApiError(f"未找到玩家 [{nickname}]")
    body = data.get("body")
    if not isinstance(body, dict):
        raise GTAOLApiError("玩家信息查询 响应缺少 body")
    return body


async def get_recent(nickname: str, platform: str = "pc") -> Optional[dict[str, Any]]:
    """获取有效期内最新快照摘要，若无则返回 None。"""
    data = await _get(
        "/api/recent",
        {
            "nickname": nickname,
            "type": "index",
            "expire": 7200,
            "timeout": 1,
            "platform": platform,
        },
    )
    _require_ok(data, "快照摘要查询")
    body = data.get("body")
    if isinstance(body, dict) and body.get("索引"):
        return body
    return None


def get_latest_index_from_status(
    body: dict[str, Any],
    platform: Optional[str] = None,
) -> Optional[str]:
    """从 status 响应中提取最新一条可用快照索引；传入 platform 时严格只取该平台。"""
    records = body.get("数据记录")
    if not isinstance(records, list) or not records:
        return None

    for item in records:
        if not isinstance(item, dict):
            continue
        # 指定平台时仅接受该平台记录
        if platform:
            item_plat = str(item.get("平台", "")).lower()
            if item_plat and item_plat != platform.lower():
                continue
        # 状态可用
        if item.get("代号") == 200 or item.get("状态") == "可用":
            index = item.get("索引")
            if isinstance(index, str) and index.strip():
                return index.strip()

    return None


async def post_query(nickname: str, platform: str = "pcalt") -> None:
    """提交玩家数据抓取队列请求。"""
    data = await _get(
        "/api/post",
        {
            "nickname": nickname,
            "platform": platform,
            "expire": 7200,
        },
    )
    if not isinstance(data, dict):
        raise GTAOLApiError("提交查询响应异常")
    if data.get("code") not in (200, 202):
        message = data.get("message", "未知错误")
        raise GTAOLApiError(f"提交查询失败 [code={data.get('code')}]: {message}")


async def get_snapshot(index: str) -> dict[str, Any]:
    """拉取全量快照 JSON。"""
    data = await _get("/api/index", {"index": index, "type": "all"})
    _require_ok(data, "快照查询")
    return data


async def poll_index(nickname: str, platform: str = "pcalt") -> Optional[str]:
    """轮询等待最新快照索引生成。"""
    for attempt in range(1, POLL_MAX_TIMES + 1):
        logger.debug(f"[GTAOnline · 数据拉取] 轮询 {nickname} 第 {attempt}/{POLL_MAX_TIMES} 次")
        recent = await get_recent(nickname, platform=platform)
        if recent and recent.get("索引"):
            return str(recent["索引"])

        status_body = await get_status(nickname)
        if status_body:
            index = get_latest_index_from_status(status_body, platform=platform)
            if index:
                return index

        await asyncio.sleep(POLL_INTERVAL)

    return None
