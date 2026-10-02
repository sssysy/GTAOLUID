from typing import Optional

from gsuid_core.logger import logger

from ..utils.helpers.api import (
    get_status,
    poll_index,
    post_query,
    get_snapshot,
    get_latest_index_from_status,
)
from ..utils.database.models import GTAUser
from ..utils.helpers.platform import (
    get_platform_api,
    get_platform_name,
    normalize_platform,
    format_platform_guide,
)
from ..utils.helpers.player_data import save_player_snapshot


async def bind_account_service(
    bot_id: str,
    user_id: str,
    game_id: str,
    raw_platform: Optional[str] = None,
) -> str:
    """处理账号绑定逻辑，并按规范同步玩家快照数据。"""
    plat_code = normalize_platform(raw_platform)
    plat_name = get_platform_name(plat_code)
    plat_api = get_platform_api(plat_code)

    # 1. 写入或覆盖数据库绑定
    await GTAUser.bind_account(
        user_id=user_id,
        bot_id=bot_id,
        game_id=game_id,
        platform=plat_code,
    )

    # 2. 检查并同步快照：有历史快照直接下载最新一条；无历史快照则触发一次后台拉取
    status_body = await get_status(game_id)
    latest_index = get_latest_index_from_status(status_body, platform=plat_api)

    if latest_index:
        logger.info(f"[GTAOnline · 账户绑定] 发现已有快照 {latest_index}，直接下载至本地")
        data = await get_snapshot(latest_index)
        save_player_snapshot(game_id, latest_index, data)
    else:
        logger.info(f"[GTAOnline · 账户绑定] {game_id} 无历史快照，触发一次异步拉取")
        await post_query(game_id, platform=plat_api)
        idx = await poll_index(game_id, platform=plat_api)
        if idx:
            data = await get_snapshot(idx)
            save_player_snapshot(game_id, idx, data)

    # 3. 组织成功提示
    guide = format_platform_guide()
    msg = (
        f"绑定GTAOL账户 [{game_id}] 成功！\n"
        f"当前绑定的平台为：[{plat_name}]\n"
        f"如果需要绑定其他平台，请附带对应平台代码\n"
        f"{guide}"
    )
    return msg


async def unbind_account_service(
    bot_id: str,
    user_id: str,
    game_id: Optional[str] = None,
) -> str:
    """处理账号解绑逻辑，并在解绑主账号时自动顺位继承。"""
    code, deleted_name, new_main_name = await GTAUser.unbind_account(
        user_id=user_id,
        bot_id=bot_id,
        game_id=game_id,
    )

    if code == -1:
        return "您当前暂无绑定的GTAOL账户。"
    if code == -2:
        return f"未找到名为 [{game_id}] 的绑定账户。"

    # 检查是否还有剩余绑定
    remaining_accounts = await GTAUser.get_user_accounts(
        user_id=user_id,
        bot_id=bot_id,
    )

    if new_main_name:
        return f"已成功解绑主账户 [{deleted_name}]！已顺位将账户 [{new_main_name}] 设为主账户。"

    if not remaining_accounts:
        return f"已成功解绑账户 [{deleted_name}]！您当前暂无绑定的GTAOL账户。"

    return f"已成功解绑账户 [{deleted_name}]！"
