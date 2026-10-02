"""GTAOL 数据刷新命令。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from .refresh_services import refresh_player_data_service
from ..utils.database.models import GTAUser

sv_gtaol_refresh = SV("GTAOL数据刷新")


@sv_gtaol_refresh.on_fullmatch("刷新数据", block=True)
async def gtaol_refresh_data(bot: Bot, ev: Event) -> None:
    main_acc = await GTAUser.get_main_account(user_id=ev.user_id, bot_id=ev.bot_id)
    if main_acc is None:
        await bot.send("您尚未绑定GTAOL账户，请先使用 gta绑定 <游戏ID> 进行绑定。")
        return

    await bot.send(f"正在刷新 [{main_acc.game_id}] 的数据，请稍候……")
    try:
        msg = await refresh_player_data_service(bot_id=ev.bot_id, user_id=ev.user_id)
        await bot.send(msg)
    except Exception as e:
        logger.exception(f"[GTAOnline · 数据刷新] 用户 {ev.user_id} 刷新异常: {e}")
        await bot.send("刷新数据时发生错误，请稍后重试。")
