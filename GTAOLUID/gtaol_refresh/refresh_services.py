from gsuid_core.logger import logger

from ..utils.helpers.api import (
    GTAOLApiError,
    poll_index,
    post_query,
    get_snapshot,
)
from ..utils.database.models import GTAUser
from ..utils.helpers.platform import get_platform_api
from ..utils.helpers.player_data import save_player_snapshot


async def refresh_player_data_service(bot_id: str, user_id: str) -> str:
    """向服务端发起异步刷新入队，轮询获取最新快照并持久化到本地 playerdata 目录。"""
    main_acc = await GTAUser.get_main_account(user_id=user_id, bot_id=bot_id)
    if main_acc is None:
        return "您尚未绑定GTAOL账户，请先使用 gta绑定 <游戏ID> 进行绑定。"

    game_id = main_acc.game_id
    plat_api = get_platform_api(main_acc.platform)

    logger.info(f"[GTAOnline · 数据刷新] 提交异步查询: {game_id} (平台: {plat_api})")
    try:
        await post_query(game_id, platform=plat_api)
        index = await poll_index(game_id, platform=plat_api)
        if not index:
            return f"刷新超时：[{game_id}] 的新数据在 2 分钟内未就绪，请稍后再试。"

        data = await get_snapshot(index)
        save_player_snapshot(game_id, index, data)
        logger.info(f"[GTAOnline · 数据刷新] {game_id} 刷新成功并落盘，快照索引: {index}")
        return f"[{game_id}] 的数据刷新成功！快照索引：[{index}]"
    except GTAOLApiError as e:
        return f"刷新失败：{e}"
    except Exception as e:
        logger.exception(f"[GTAOnline · 数据刷新] 刷新 {game_id} 异常: {e}")
        return "刷新数据时发生错误，请稍后重试。"
