import asyncio
from typing import Any, Callable, Awaitable, Dict, List, Tuple, Optional

from gsuid_core.logger import logger

from ..utils.helpers.api import (
    GTAOLApiError,
    get_status,
    poll_index,
    post_query,
    get_snapshot,
    get_latest_index_from_status,
)
from ..utils.helpers.avatar import load_avatar_data_uri
from ..utils.database.models import GTAUser
from ..utils.helpers.platform import (
    get_platform_api,
    get_platform_name,
    normalize_platform,
    format_platform_guide,
)
from ..utils.utils.user_avatar import get_core_user_name, get_core_user_avatar
from ..utils.render.HTML.render import render_bind_list_card
from ..utils.helpers.player_data import save_player_snapshot, extract_account_profile


async def _save_account_profile(
    bot_id: str,
    user_id: str,
    game_id: str,
    snapshot: Dict[str, Any],
) -> None:
    """把快照中的 Rockstar 资料写回绑定记录。"""
    profile = extract_account_profile(snapshot)
    await GTAUser.update_account_profile(
        user_id=user_id,
        bot_id=bot_id,
        game_id=game_id,
        **profile,
    )


async def bind_account_service(
    bot_id: str,
    user_id: str,
    game_id: str,
    raw_platform: Optional[str] = None,
    on_first_fetch: Optional[Callable[[], Awaitable[Any]]] = None,
) -> str:
    """校验玩家数据可用后写入绑定记录；取不到快照视为绑定失败，不落库。

    Args:
        on_first_fetch: 进入首次拉取快照分支时的进度回调，可为 None。
    """
    plat_code = normalize_platform(raw_platform)
    plat_name = get_platform_name(plat_code)
    plat_api = get_platform_api(plat_code)

    # 1. 校验玩家并获取快照索引：有历史快照直接取用，无历史快照则触发一次异步拉取
    status_body = await get_status(game_id)
    latest_index = get_latest_index_from_status(status_body, platform=plat_api)

    if not latest_index:
        logger.info(f"[GTAOnline · 账户绑定] {game_id} 无历史快照，触发一次异步拉取")
        if on_first_fetch is not None:
            await on_first_fetch()
        await post_query(game_id, platform=plat_api)
        latest_index = await poll_index(game_id, platform=plat_api)

    if not latest_index:
        raise GTAOLApiError(f"未在 2 分钟内获取到 [{game_id}] 的玩家数据，请稍后重试")

    # 2. 快照确认可用后才写入绑定，避免绑定失败留下记录
    data = await get_snapshot(latest_index)
    save_player_snapshot(game_id, latest_index, data)

    await GTAUser.bind_account(
        user_id=user_id,
        bot_id=bot_id,
        game_id=game_id,
        platform=plat_code,
    )
    await _save_account_profile(bot_id, user_id, game_id, data)

    # 3. 组织成功提示
    guide = format_platform_guide()
    msg = (
        f"绑定GTAOL账户 [{game_id}] 成功！\n"
        f"当前绑定的平台为：[{plat_name}]\n"
        f"如果需要绑定其他平台，请附带对应平台代码\n"
        f"{guide}\n"
        f"如：gta绑定 sssysy 1"
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
        return f"已成功解绑主账户 [{deleted_name}]！\n已顺位将账户 [{new_main_name}] 设为主账户。"

    if not remaining_accounts:
        return f"已成功解绑账户 [{deleted_name}]！您当前暂无绑定的GTAOL账户。"

    return f"已成功解绑账户 [{deleted_name}]！"


async def render_bind_list_service(
    bot_id: str,
    user_id: str,
) -> Tuple[Optional[bytes], str]:
    """生成用户绑定账号列表图片。

    Returns:
        Tuple[Optional[bytes], str]: (渲染图片字节流, 提示或错误消息)
    """
    accounts = await GTAUser.get_user_accounts(user_id=user_id, bot_id=bot_id)
    if not accounts:
        return None, "您当前暂无绑定的GTAOL账户，请先使用 gta绑定 <游戏ID> 进行绑定。"

    logger.info(f"[GTAOnline · 账户绑定] 为用户 {user_id} 生成绑定列表，共 {len(accounts)} 个账号")
    try:
        # 1. 用户身份信息取框架用户管理
        user_name = await get_core_user_name(user_id)
        user_avatar_src = await load_avatar_data_uri(await get_core_user_avatar(user_id))

        # 2. 账号卡片只读绑定记录，头像取绑定/刷新时已存下的地址
        avatar_srcs = await asyncio.gather(*[load_avatar_data_uri(acc.avatar_url) for acc in accounts])
        items: List[Dict[str, Any]] = [
            {
                "name": acc.game_id,
                "rid": acc.rockstar_id or "None",
                "avatar_src": avatar_src,
            }
            for acc, avatar_src in zip(accounts, avatar_srcs)
        ]

        data: Dict[str, Any] = {
            "user_name": user_name,
            "user_id": user_id,
            "user_avatar_src": user_avatar_src,
            "accounts": items,
        }
        img_bytes = await render_bind_list_card(data)
        return img_bytes, "OK"
    except Exception as e:
        logger.exception(f"[GTAOnline · 账户绑定] 渲染绑定列表异常: {e}")
        return None, "生成绑定账号列表图片失败，请稍后重试。"
