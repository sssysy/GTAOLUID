"""GTAOL 玩家数据总览命令。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment

from .info_services import (
    render_detail_service,
    render_overview_service,
    render_snapshot_list_service,
    render_finance_detail_service,
)
from ..utils.helpers.api import GTAOLApiError

sv_gtaol_info = SV("GTAOL玩家信息")


@sv_gtaol_info.on_command("总览", block=True)
async def gtaol_player_overview(bot: Bot, ev: Event) -> None:
    target_id = ev.text.strip() or None
    try:
        img_bytes, msg = await render_overview_service(
            bot_id=ev.bot_id,
            user_id=ev.user_id,
            target_game_id=target_id,
        )
        if img_bytes is not None:
            await bot.send(MessageSegment.image(img_bytes))
        else:
            await bot.send(msg)
    except Exception as e:
        logger.exception(f"[GTAOnline · 数据总览] 生成总览图异常: {e}")
        await bot.send("生成总览卡片失败，请稍后重试。")


@sv_gtaol_info.on_command("玩家详情", block=True)
async def gtaol_player_detail(bot: Bot, ev: Event) -> None:
    target_id = ev.text.strip() or None
    try:
        img_bytes, msg = await render_detail_service(
            bot_id=ev.bot_id,
            user_id=ev.user_id,
            target_game_id=target_id,
        )
        if img_bytes is not None:
            await bot.send(MessageSegment.image(img_bytes))
        else:
            await bot.send(msg)
    except Exception as e:
        logger.exception(f"[GTAOnline · 玩家详情] 生成详情图异常: {e}")
        await bot.send("生成玩家详情卡片失败，请稍后重试。")


@sv_gtaol_info.on_command("收支差", block=True)
async def gtaol_player_finance(bot: Bot, ev: Event) -> None:
    target_id = ev.text.strip() or None
    try:
        img_bytes, msg = await render_finance_detail_service(
            bot_id=ev.bot_id,
            user_id=ev.user_id,
            target_game_id=target_id,
        )
        if img_bytes is not None:
            await bot.send(MessageSegment.image(img_bytes))
        else:
            await bot.send(msg)
    except Exception as e:
        logger.exception(f"[GTAOnline · 收支差] 生成收支差图异常: {e}")
        await bot.send("生成收支差卡片失败，请稍后重试。")


@sv_gtaol_info.on_command("快照列表", block=True)
async def gtaol_snapshot_list(bot: Bot, ev: Event) -> None:
    target_id = ev.text.strip() or None
    try:
        img_bytes, msg = await render_snapshot_list_service(
            bot_id=ev.bot_id,
            user_id=ev.user_id,
            target_game_id=target_id,
        )
        if img_bytes is not None:
            await bot.send(MessageSegment.image(img_bytes))
        else:
            await bot.send(msg)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 快照列表] 用户 {ev.user_id} 查询失败: {e}")
        await bot.send(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 快照列表] 生成快照列表异常: {e}")
        await bot.send("运行出错，生成快照列表失败，请稍后重试。")
