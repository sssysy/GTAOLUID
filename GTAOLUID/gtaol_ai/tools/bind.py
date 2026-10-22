"""GTAOL 账户绑定 AI 工具。"""

from typing import Any, Dict

from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.ai_core.models import ToolContext
from gsuid_core.ai_core.register import ai_tools

from ._common import ai_error, check_sv
from ...gtaol_bind import sv_gtaol_bind
from ...utils.helpers.api import GTAOLApiError
from ...gtaol_bind.bind_services import get_bind_list_data_service


def _check_gtaol_bind(ev: Event) -> tuple[bool, str]:
    """校验账户绑定 AI 工具权限。"""
    return check_sv(ev, sv_gtaol_bind, "GTAOL 账户绑定")


@ai_tools(
    category="gtaol",
    capability_domain="GTAOL数据查询",
    covers=["GTAOL 当前用户已绑定账号、游戏ID、Rockstar ID、平台与主账号状态"],
    check_func=_check_gtaol_bind,
)
async def query_gtaol_bound_accounts(ctx: ToolContext) -> Dict[str, Any]:
    """查询当前用户已绑定的 GTAOL 账号列表。"""
    ev = ctx.ev
    if ev is None:
        return ai_error("缺少会话上下文，无法查询绑定账号。")

    try:
        data, msg = await get_bind_list_data_service(ev.bot_id, ev.user_id)
    except GTAOLApiError as e:
        logger.warning(f"[GTAOnline · 账户绑定] AI 查询失败: {e}")
        return ai_error(f"运行出错：{e}")
    except Exception as e:
        logger.exception(f"[GTAOnline · 账户绑定] AI 查询异常: {e}")
        return ai_error("运行出错，查询绑定账号失败，请稍后重试。")
    if data is None:
        return ai_error(msg)

    accounts = [{key: value for key, value in account.items() if key != "avatar_url"} for account in data["accounts"]]
    return {"ok": True, "accounts": accounts}
