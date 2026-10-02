"""GTAOL 账户绑定与解绑命令。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from .bind_services import bind_account_service, unbind_account_service
from ..utils.helpers.api import GTAOLApiError

sv_gtaol_bind = SV("GTAOL账户绑定")


@sv_gtaol_bind.on_prefix("绑定", block=True)
async def gtaol_bind_account(bot: Bot, ev: Event) -> None:
    text = ev.text.strip()
    if not text:
        await bot.send("请在命令后附带游戏ID。\n例如：gta绑定 <游戏ID> (平台代码)")
        return

    parts = text.split()
    game_id = parts[0]
    platform = parts[1] if len(parts) > 1 else ""

    await bot.send(f"正在为 [{game_id}] 验证并同步数据，请稍候……")
    try:
        msg = await bind_account_service(
            bot_id=ev.bot_id,
            user_id=ev.user_id,
            game_id=game_id,
            raw_platform=platform,
        )
        await bot.send(msg)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 账户绑定] 用户 {ev.user_id} 绑定 {game_id} 同步失败: {e}")
        await bot.send(f"绑定已记录，但玩家数据同步失败：{e}\n可稍后使用 gta刷新数据 重试。")
    except Exception as e:
        logger.exception(f"[GTAOnline · 账户绑定] 用户 {ev.user_id} 绑定 {game_id} 异常: {e}")
        await bot.send("绑定过程出现异常，请稍后重试。")


@sv_gtaol_bind.on_command("解绑", block=True)
async def gtaol_unbind_account(bot: Bot, ev: Event) -> None:
    target_id = ev.text.strip() or None
    try:
        msg = await unbind_account_service(
            bot_id=ev.bot_id,
            user_id=ev.user_id,
            game_id=target_id,
        )
        await bot.send(msg)
    except Exception as e:
        logger.exception(f"[GTAOnline · 账户绑定] 用户 {ev.user_id} 解绑异常: {e}")
        await bot.send("解绑过程出现异常，请稍后重试。")
