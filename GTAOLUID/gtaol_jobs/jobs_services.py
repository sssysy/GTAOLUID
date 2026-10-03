"""GTAOL 社区差事查询、编号缓存与卡片数据组装。"""

from typing import Any
from datetime import datetime, timezone, timedelta

import httpx

from gsuid_core.logger import logger

from .jobs_helpers import (
    JobsFilter,
    get_mode_name,
    parse_jobs_filter,
    get_vehicle_class_name,
    image_path_to_data_uri,
    load_job_image_data_uri,
)
from ..utils.downloader import download
from ..utils.helpers.api import GTAOLApiError
from ..utils.helpers.avatar import load_avatar_data_uri
from ..utils.render.HTML.render import render_jobs_list_card, render_jobs_detail_card

SC_API_BASE = "https://scapi.rockstargames.com"
_SEARCH_URL = f"{SC_API_BASE}/search/mission"
_DETAIL_URL = f"{SC_API_BASE}/ugc/mission/details"

# 社区接口强制校验 X-AMC 与站点来路，缺任一项返回 403
_HEADERS = {
    "Accept": "application/json",
    "X-Requested-With": "XMLHttpRequest",
    "X-Lang": "zh-CN",
    "X-AMC": "true",
    "Origin": "https://socialclub.rockstargames.com",
    "Referer": "https://socialclub.rockstargames.com/",
    "Cookie": "UAGC=1",
}
_TIMEOUT = httpx.Timeout(30.0)

# 列表卡固定三列七行，只取一页
PAGE_SIZE = 21

_DETAIL_USAGE = "请在命令后附带差事编号。\n例如：gta差事详情 1"

# 用户 -> {编号: 差事 ID}缓存
_JOB_INDEX_CACHE: dict[str, dict[int, str]] = {}

_BEIJING = timezone(timedelta(hours=8))


async def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """请求社区接口并返回 JSON；连接异常与格式异常统一转为可展示错误。"""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
            resp = await client.get(url, params=params)
    except httpx.HTTPError as e:
        logger.warning(f"[GTAOnline · 差事查询] 社区接口请求失败: {e!r}")
        raise GTAOLApiError("社区接口连接失败，请稍后重试") from e

    if resp.status_code != 200:
        raise GTAOLApiError(f"社区接口返回异常 [HTTP {resp.status_code}]")
    try:
        data = resp.json()
    except ValueError as e:
        raise GTAOLApiError("社区接口返回格式异常") from e
    if not isinstance(data, dict):
        raise GTAOLApiError("社区接口返回格式异常")
    return data


def _build_list_item(item: dict[str, Any], users: dict[str, Any]) -> dict[str, Any]:
    """把单条搜索结果整理成列表卡字段。"""
    author = users.get(str(item.get("userId"))) or {}
    like = int(item.get("likeCount") or 0)
    dislike = int(item.get("dislikeCount") or 0)
    total = like + dislike
    return {
        "id": item.get("id") or "",
        "name": item.get("name") or "",
        "img": item.get("imgSrc") or "",
        "author": author.get("nickname") or "",
        "mode": get_mode_name(item.get("type")) or "",
        "played": int(item.get("playedCount") or 0),
        "rate": round(like / total * 100) if total > 0 else 0,
    }


async def _search_jobs(filters: JobsFilter) -> list[dict[str, Any]]:
    """按筛选条件查询一页社区差事。"""
    params: dict[str, Any] = {
        "title": "gtav",
        "platform": "pcalt",
        "dateRangeCreated": filters.date_range,
        "sort": filters.sort,
        "pageIndex": 0,
        "pageSize": PAGE_SIZE,
        "searchTerm": "",
    }
    if filters.source:
        params["filter"] = filters.source
    if filters.mission_type:
        params["missiontype"] = filters.mission_type
    if filters.subtype:
        params["subtype"] = filters.subtype

    data = await _get_json(_SEARCH_URL, params)
    content = data.get("content")
    if not isinstance(content, dict) or not isinstance(content.get("items"), list):
        raise GTAOLApiError("差事列表响应格式异常")

    users = content.get("users") or {}
    return [_build_list_item(item, users) for item in content["items"] if isinstance(item, dict)]


def _format_utc_to_local(value: Any) -> str | None:
    """ISO8601 UTC 转北京时间；解析失败返回 None。"""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(_BEIJING)
    except ValueError:
        return None
    return moment.strftime("%Y-%m-%d %H:%M")


def _format_players(gen: dict[str, Any]) -> str | None:
    """人数区间；上下限缺任一项返回 None。"""
    low, high = gen.get("min"), gen.get("num")
    if low is None or high is None:
        return None
    low, high = int(low), int(high)
    return f"{low} 人" if low == high else f"{low} - {high} 人"


def _format_teams(gen: dict[str, Any]) -> str | None:
    """队伍数；缺值时返回 None。"""
    teams = gen.get("tnum")
    if teams is None:
        return None
    return f"{int(teams)} 队"


def _join_names(values: Any, translate=None) -> str | None:
    """列表值去空去重后用顿号拼接；未收录的枚举值原样保留。"""
    if not isinstance(values, list):
        return None
    names = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        names.append(translate(text) if translate else text)
    names = [name for name in dict.fromkeys(names) if name]
    return "、".join(names) if names else None


def _build_detail_rows(content: dict[str, Any]) -> list[dict[str, str]]:
    """按可获取性组装详情信息行，缺值项不入列。"""
    data = content.get("data") or {}
    mission = data.get("mission") or {}
    gen = mission.get("gen") or {}
    race = mission.get("race") or {}
    meta = data.get("meta") or {}

    rows: list[tuple[str, Any]] = [
        ("ID", content.get("id")),
        ("模式", get_mode_name(content.get("type"))),
        ("制作日期", _format_utc_to_local(content.get("rootCreatedDate"))),
        ("修改日期", _format_utc_to_local(content.get("createdDate"))),
        ("人数", _format_players(gen)),
        ("队伍数", _format_teams(gen)),
    ]
    # 非竞速差事的 race 段存在但路线与圈数均为 0，按无值处理
    if race.get("rdis"):
        rows.append(("路线类型", "绕圈" if race.get("isLapsRace") else "点对点"))
        rows.append(("路线长度", f"{float(race['rdis']) / 1000:.2f} 公里"))
    if race.get("lap"):
        rows.append(("圈数", f"{race['lap']} 圈"))
    rows.append(("载具类型", _join_names(meta.get("vehcl"), get_vehicle_class_name)))
    rows.append(("武器类型", _join_names(meta.get("wpcl"))))
    rows.append(("标签", _join_names(content.get("userTags"))))

    return [{"label": label, "value": str(value)} for label, value in rows if value]


async def render_jobs_list_service(user_id: str, text: str) -> tuple[bytes | None, str]:
    """渲染差事推荐列表；条件冲突、查询为空等预期失败返回提示文案。"""
    filters = parse_jobs_filter(text)
    if filters.conflicts:
        return None, "\n".join(filters.conflicts)

    jobs = await _search_jobs(filters)
    if not jobs:
        return None, "没有查询到符合条件的差事，请调整筛选条件后重试。"

    _JOB_INDEX_CACHE[user_id] = {index: job["id"] for index, job in enumerate(jobs, start=1)}

    paths = await download([job["img"] for job in jobs], max_concurrency=8)
    rows = [
        {
            "index": index,
            "id": job["id"],
            "name": job["name"],
            "author": job["author"],
            "mode": job["mode"],
            "played": job["played"],
            "rate": job["rate"],
            "img_uri": image_path_to_data_uri(paths[index - 1]),
        }
        for index, job in enumerate(jobs, start=1)
    ]

    filter_line = f"筛选：{' · '.join(filters.matched_labels)}" if filters.matched_labels else ""
    return await render_jobs_list_card({"jobs": rows, "filter_line": filter_line}), ""


async def render_jobs_detail_service(user_id: str, text: str) -> tuple[bytes | None, str]:
    """渲染差事详情卡；编号非法或缓存失效时返回提示文案。"""
    raw = (text or "").strip()
    if not raw.isdigit():
        return None, _DETAIL_USAGE

    job_id = _JOB_INDEX_CACHE.get(user_id, {}).get(int(raw))
    if not job_id:
        return None, "编号已失效，请先发送差事推荐后再查看详情。"

    data = await _get_json(_DETAIL_URL, {"title": "gtav", "contentId": job_id})
    content = data.get("content")
    if not isinstance(content, dict):
        raise GTAOLApiError("差事详情响应格式异常")

    users = data.get("users") or {}
    author = users.get(str(content.get("userId"))) or {}
    like = int(content.get("likeCount") or 0)
    dislike = int(content.get("dislikeCount") or 0)
    total = like + dislike

    payload = {
        "name": content.get("name") or "",
        "desc": content.get("desc") or "",
        "img_uri": await load_job_image_data_uri(content.get("imgSrc")),
        "author": author.get("nickname") or "",
        "author_avatar": await load_avatar_data_uri(author.get("avatarUrl")),
        "like": like,
        "dislike": dislike,
        "rate": round(like / total * 100) if total > 0 else 0,
        "rows": _build_detail_rows(content),
    }
    return await render_jobs_detail_card(payload), ""
