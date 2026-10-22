"""GTAOL 社区差事推荐与详情命令。"""

from gsuid_core.sv import SV
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.segment import MessageSegment

from .jobs_services import (
    render_jobs_list_service,
    render_jobs_detail_service,
)
from ..utils.helpers.api import GTAOLApiError

sv_gtaol_jobs = SV("GTAOL差事")


async def _send_jobs_recommend(bot: Bot, ev: Event) -> None:
    """请求并回传差事推荐列表图片。"""
    try:
        img_bytes, msg = await render_jobs_list_service(user_id=ev.user_id, text=ev.text)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 差事推荐] 用户 {ev.user_id} 查询失败: {e}")
        await bot.send(f"查询失败：{e}", at_sender=True)
        return
    except Exception as e:
        logger.exception(f"[GTAOnline · 差事推荐] 用户 {ev.user_id} 查询异常: {e}")
        await bot.send("查询过程出现异常，请稍后重试。", at_sender=True)
        return

    if img_bytes is not None:
        await bot.send(MessageSegment.image(img_bytes))
    else:
        await bot.send(msg, at_sender=True)


@sv_gtaol_jobs.on_suffix(
    "差事推荐",
    block=True,
    to_ai="""
    生成 GTAOL 社区差事推荐卡片图片，仅在用户明确要求查看推荐卡片或图片时调用。
    筛选词只使用插件已支持的时间范围、来源、排序、差事类型和子类型。

    Args:
        text: 筛选条件，例如“上周热门竞速”；无筛选时传空字符串。
    """,
    covers=["Rockstar 社区差事推荐列表、筛选条件、差事编号与卡片"],
)
async def gtaol_jobs_recommend_by_filter(bot: Bot, ev: Event) -> None:
    await _send_jobs_recommend(bot, ev)


@sv_gtaol_jobs.on_fullmatch("差事推荐", block=True)
async def gtaol_jobs_recommend_all(bot: Bot, ev: Event) -> None:
    await _send_jobs_recommend(bot, ev)


@sv_gtaol_jobs.on_prefix(
    "差事详情",
    block=True,
    to_ai="""
    按推荐列表编号生成 GTAOL 社区差事详情卡片图片，仅在用户明确要求查看详情卡片或图片时调用。
    必须先调用差事推荐工具，再使用返回列表中的编号。

    Args:
        text: 差事推荐列表中的编号，例如 1。
    """,
    covers=["Rockstar 社区差事详情卡片、作者、点赞率、人数、载具、武器与标签"],
)
async def gtaol_job_detail(bot: Bot, ev: Event) -> None:
    text = ev.text.strip()
    if not text:
        return

    try:
        img_bytes, msg = await render_jobs_detail_service(user_id=ev.user_id, text=text)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 差事详情] 用户 {ev.user_id} 查询 {text} 失败: {e}")
        await bot.send(f"查询失败：{e}", at_sender=True)
        return
    except Exception as e:
        logger.exception(f"[GTAOnline · 差事详情] 用户 {ev.user_id} 查询 {text} 异常: {e}")
        await bot.send("查询过程出现异常，请稍后重试。", at_sender=True)
        return

    if img_bytes is not None:
        await bot.send(MessageSegment.image(img_bytes))
    else:
        await bot.send(msg, at_sender=True)
