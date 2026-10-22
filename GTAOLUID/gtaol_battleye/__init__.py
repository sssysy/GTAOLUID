"""GTAOL 战眼封禁查询命令。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event

from .battleye_services import check_battleye_service
from ..utils.helpers.api import GTAOLApiError

sv_gtaol_battleye = SV("GTAOL战眼查询")


@sv_gtaol_battleye.on_command(
    ("查封禁", "查战眼"),
    block=True,
    to_ai="""
    查询 GTAOL 玩家的战眼 [BattlEye] 封禁状态与封禁原因。
    用户提供游戏昵称或 RID 时使用该目标；未提供时查询当前用户主账号。

    Args:
        text: 游戏昵称或 RID；查询当前用户主账号时传空字符串。
    """,
    covers=["GTAOL BattlEye 战眼封禁状态、封禁原因、游戏昵称与 RID"],
)
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
