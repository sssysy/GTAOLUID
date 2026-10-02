"""GTAOL 战眼封禁查询命令。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from .battleye_services import check_battleye_service
from ..utils.helpers.api import GTAOLApiError

sv_gtaol_battleye = SV("GTAOL战眼查询")


@sv_gtaol_battleye.on_command(("查封禁", "查战眼"), block=True)
async def gtaol_battleye_check(bot: Bot, ev: Event) -> None:
    try:
        msg = await check_battleye_service(
            bot_id=ev.bot_id,
            user_id=ev.user_id,
            identifier=ev.text.strip() or None,
        )
        await bot.send(msg)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 战眼查询] 用户 {ev.user_id} 查询失败: {e}")
        await bot.send(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 战眼查询] 用户 {ev.user_id} 查询异常: {e}")
        await bot.send("运行出错，请稍后重试。")
