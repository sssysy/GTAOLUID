"""GTAOL 玩家数据总览命令。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment

from .info_services import render_detail_service, render_overview_service

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
