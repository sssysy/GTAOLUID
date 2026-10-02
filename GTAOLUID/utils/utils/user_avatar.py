"""框架用户管理中的用户头像与用户名读取。"""

from typing import Optional

from gsuid_core.utils.database.models import CoreUser


async def get_core_user_avatar(user_id: str) -> Optional[str]:
    """按 user_id 从框架用户管理读取头像 URL；无有效 URL 时返回 None"""
    if not user_id:
        return None

    rows = await CoreUser.select_rows(user_id=user_id)
    if not rows:
        return None

    for row in rows:
        icon = (row.user_icon or "").strip()
        if icon.startswith(("http://", "https://")):
            return icon

    return None


async def get_core_user_name(user_id: str) -> Optional[str]:
    """按 user_id 从框架用户管理读取用户名；无有效名称时返回 None"""
    if not user_id:
        return None

    rows = await CoreUser.select_rows(user_id=user_id)
    if not rows:
        return None

    for row in rows:
        name = (row.user_name or "").strip()
        # 框架默认占位名 "1" 视为未设置
        if name and name != "1":
            return name

    return None
