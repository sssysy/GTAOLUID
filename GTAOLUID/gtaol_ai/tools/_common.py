"""GTAOL AI 工具共用校验与返回结构。"""

from typing import Any, Dict

from gsuid_core.sv import SV
from gsuid_core.models import Event


def ai_error(message: str) -> Dict[str, Any]:
    """构造 AI 工具错误返回体。"""
    return {"ok": False, "message": message}


def check_sv(ev: Event, sv: SV, feature_name: str) -> tuple[bool, str]:
    """校验 AI 工具调用是否满足插件与 SV 权限。"""
    if not sv.plugins.enabled:
        return False, "GTAOLUID 插件已禁用。"
    if not sv.enabled:
        return False, f"{feature_name}功能已禁用。"
    if ev.user_pm > sv.plugins.pm:
        return False, f"权限不足：该插件需要权限等级 {sv.plugins.pm}。"
    if ev.user_pm > sv.pm:
        return False, f"权限不足：该功能需要权限等级 {sv.pm}。"
    return True, ""
