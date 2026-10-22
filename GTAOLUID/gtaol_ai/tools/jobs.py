"""GTAOL 社区差事 AI 工具。"""

from typing import Any, Dict

from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.ai_core.models import ToolContext
from gsuid_core.ai_core.register import ai_tools

from ._common import ai_error, check_sv
from ...gtaol_jobs import sv_gtaol_jobs
from ...utils.helpers.api import GTAOLApiError
from ...gtaol_jobs.jobs_services import get_jobs_list_data_service, get_jobs_detail_data_service


def _check_gtaol_jobs(ev: Event) -> tuple[bool, str]:
    """校验差事 AI 工具权限。"""
    return check_sv(ev, sv_gtaol_jobs, "GTAOL 差事")


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["Rockstar 社区差事推荐列表、筛选条件、差事编号、作者、模式、游玩次数与好评率"],
    check_func=_check_gtaol_jobs,
    timeout=90.0,
)
async def query_gtaol_jobs(
    ctx: ToolContext,
    text: str = "",
) -> Dict[str, Any]:
    """查询 GTAOL 社区差事推荐列表。

    筛选词只使用插件已支持的时间范围、来源、排序、差事类型和子类型。

    Args:
        text: 筛选条件，例如“上周热门竞速”；无筛选时传空字符串。
    """
    ev = ctx.ev
    if ev is None:
        return ai_error("缺少会话上下文，无法查询差事推荐。")

    try:
        data, msg = await get_jobs_list_data_service(ev.user_id, text)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 差事推荐] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 差事推荐] AI 查询异常: {e}")
        return ai_error("运行出错，查询差事推荐失败，请稍后重试。")
    if data is None:
        return ai_error(msg)

    jobs = [{key: value for key, value in job.items() if key != "image_url"} for job in data["jobs"]]
    return {"ok": True, "filter": data["filter"], "jobs": jobs}


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["Rockstar 社区差事详情、作者、点赞率、人数、队伍数、载具、武器与标签"],
    check_func=_check_gtaol_jobs,
    timeout=90.0,
)
async def query_gtaol_job_detail(
    ctx: ToolContext,
    index: int,
) -> Dict[str, Any]:
    """查询 GTAOL 社区差事详情。

    必须先调用差事推荐工具，再使用返回列表中的编号。

    Args:
        index: 差事推荐列表中的编号。
    """
    ev = ctx.ev
    if ev is None:
        return ai_error("缺少会话上下文，无法查询差事详情。")

    try:
        data, msg = await get_jobs_detail_data_service(ev.user_id, str(index))
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 差事详情] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 差事详情] AI 查询异常: {e}")
        return ai_error("运行出错，查询差事详情失败，请稍后重试。")
    if data is None:
        return ai_error(msg)

    result = {key: value for key, value in data.items() if key not in ("image_url", "author_avatar_url")}
    return {"ok": True, "data": result}
