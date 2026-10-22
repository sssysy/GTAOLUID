"""GTAOL 玩家信息 AI 工具。"""

from typing import Any, Dict

from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.ai_core.models import ToolContext
from gsuid_core.ai_core.register import ai_tools

from ._common import ai_error, check_sv
from ...gtaol_info import sv_gtaol_info
from ...utils.helpers.api import GTAOLApiError
from ...gtaol_info.info_services import (
    get_detail_data_service,
    get_finance_data_service,
    get_overview_data_service,
    get_snapshot_list_data_service,
    get_snapshot_detail_data_service,
    get_snapshot_finance_data_service,
    get_snapshot_overview_data_service,
)


def _check_gtaol_info(ev: Event) -> tuple[bool, str]:
    """校验玩家信息 AI 工具权限。"""
    return check_sv(ev, sv_gtaol_info, "GTAOL 玩家信息")


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["GTAOL 玩家等级、现金、银行、资产、技能、战斗、载具、通缉、竞技与奖章数据"],
    check_func=_check_gtaol_info,
)
async def query_gtaol_player_overview(
    ctx: ToolContext,
    game_id: str = "",
) -> Dict[str, Any]:
    """查询 GTAOL 玩家总览数据。

    Args:
        game_id: 目标游戏ID；为空时查询当前用户的主账号。
    """
    ev = ctx.ev
    if ev is None:
        return ai_error("缺少会话上下文，无法查询玩家总览。")

    try:
        data, msg = await get_overview_data_service(ev.bot_id, ev.user_id, game_id)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 数据总览] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 数据总览] AI 查询异常: {e}")
        return ai_error("运行出错，查询玩家总览失败，请稍后重试。")
    if data is None:
        return ai_error(msg)
    return {"ok": True, "data": data}


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["GTAOL 玩家详情、全量快照字段与细项统计"],
    check_func=_check_gtaol_info,
)
async def query_gtaol_player_detail(
    ctx: ToolContext,
    game_id: str = "",
) -> Dict[str, Any]:
    """查询 GTAOL 玩家详细数据。

    Args:
        game_id: 目标游戏ID；为空时查询当前用户的主账号。
    """
    ev = ctx.ev
    if ev is None:
        return ai_error("缺少会话上下文，无法查询玩家详情。")

    try:
        data, msg = await get_detail_data_service(ev.bot_id, ev.user_id, game_id)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 玩家详情] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 玩家详情] AI 查询异常: {e}")
        return ai_error("运行出错，查询玩家详情失败，请稍后重试。")
    if data is None:
        return ai_error(msg)
    return {"ok": True, "data": data}


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["GTAOL 玩家收入、支出、结余与收支差分类明细"],
    check_func=_check_gtaol_info,
)
async def query_gtaol_player_finance(
    ctx: ToolContext,
    game_id: str = "",
) -> Dict[str, Any]:
    """查询 GTAOL 玩家收支数据。

    Args:
        game_id: 目标游戏ID；为空时查询当前用户的主账号。
    """
    ev = ctx.ev
    if ev is None:
        return ai_error("缺少会话上下文，无法查询玩家收支。")

    try:
        data, msg = await get_finance_data_service(ev.bot_id, ev.user_id, game_id)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 收支差] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 收支差] AI 查询异常: {e}")
        return ai_error("运行出错，查询玩家收支失败，请稍后重试。")
    if data is None:
        return ai_error(msg)
    return {"ok": True, "data": data}


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["GTAOL 历史快照索引、快照ID、时间、平台与可用状态"],
    check_func=_check_gtaol_info,
    timeout=90.0,
)
async def query_gtaol_snapshot_list(
    ctx: ToolContext,
    game_id: str = "",
) -> Dict[str, Any]:
    """查询 GTAOL 玩家已有快照记录列表。

    Args:
        game_id: 目标游戏ID；为空时查询当前用户的主账号。
    """
    ev = ctx.ev
    if ev is None:
        return ai_error("缺少会话上下文，无法查询快照列表。")

    try:
        data, msg = await get_snapshot_list_data_service(ev.bot_id, ev.user_id, game_id)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 快照列表] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 快照列表] AI 查询异常: {e}")
        return ai_error("运行出错，查询快照列表失败，请稍后重试。")
    if data is None:
        return ai_error(msg)
    return {"ok": True, "data": data}


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["GTAOL 指定快照ID的玩家总览数据"],
    check_func=_check_gtaol_info,
    timeout=90.0,
)
async def query_gtaol_snapshot_overview(
    ctx: ToolContext,
    snapshot_id: str,
) -> Dict[str, Any]:
    """按快照ID查询 GTAOL 玩家总览数据。

    Args:
        snapshot_id: 快照ID，例如 BSPE6L。
    """
    target = snapshot_id.strip()
    if not target:
        return ai_error("需要提供快照ID。")

    try:
        data, msg = await get_snapshot_overview_data_service(target)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 快照总览] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 快照总览] AI 查询异常: {e}")
        return ai_error("运行出错，查询快照总览失败，请稍后重试。")
    if data is None:
        return ai_error(msg)
    return {"ok": True, "data": data}


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["GTAOL 指定快照ID的玩家详情与全量快照字段"],
    check_func=_check_gtaol_info,
    timeout=90.0,
)
async def query_gtaol_snapshot_detail(
    ctx: ToolContext,
    snapshot_id: str,
) -> Dict[str, Any]:
    """按快照ID查询 GTAOL 玩家详细数据。

    Args:
        snapshot_id: 快照ID，例如 BSPE6L。
    """
    target = snapshot_id.strip()
    if not target:
        return ai_error("需要提供快照ID。")

    try:
        data, msg = await get_snapshot_detail_data_service(target)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 快照玩家详情] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 快照玩家详情] AI 查询异常: {e}")
        return ai_error("运行出错，查询快照玩家详情失败，请稍后重试。")
    if data is None:
        return ai_error(msg)
    return {"ok": True, "data": data}


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["GTAOL 指定快照ID的收入、支出、结余与收支差数据"],
    check_func=_check_gtaol_info,
    timeout=90.0,
)
async def query_gtaol_snapshot_finance(
    ctx: ToolContext,
    snapshot_id: str,
) -> Dict[str, Any]:
    """按快照ID查询 GTAOL 玩家收支数据。

    Args:
        snapshot_id: 快照ID，例如 BSPE6L。
    """
    target = snapshot_id.strip()
    if not target:
        return ai_error("需要提供快照ID。")

    try:
        data, msg = await get_snapshot_finance_data_service(target)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 快照收支差] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 快照收支差] AI 查询异常: {e}")
        return ai_error("运行出错，查询快照收支失败，请稍后重试。")
    if data is None:
        return ai_error(msg)
    return {"ok": True, "data": data}
