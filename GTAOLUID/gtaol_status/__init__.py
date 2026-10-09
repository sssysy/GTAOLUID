"""注册 GTAOLUID 的 core 状态额外信息。"""

from pathlib import Path

from PIL import Image
from sqlmodel import col, func, select

from gsuid_core.status.plugin_status import register_status
from gsuid_core.utils.database.base_models import async_maker

from ..utils.database.models import GTAUser

_ICON = Path(__file__).parent.parent.parent / "ICON.png"

# 平台代码严格对应 utils/helpers/platform.py：0 增强版、1 传承版、2 PS 版、3 Xbox 版
PC_PLATFORMS = ("0", "1")
PS_PLATFORM = "2"
XBOX_PLATFORM = "3"


async def _count_bind_by_platform(platforms: tuple[str, ...]) -> int:
    """统计指定平台代码的绑定记录条数。"""
    async with async_maker() as session:
        stmt = select(func.count()).select_from(GTAUser).where(col(GTAUser.platform).in_(platforms))
        return int((await session.execute(stmt)).scalar_one())


async def get_pc_bind_num() -> int:
    return await _count_bind_by_platform(PC_PLATFORMS)


async def get_ps_bind_num() -> int:
    return await _count_bind_by_platform((PS_PLATFORM,))


async def get_xbox_bind_num() -> int:
    return await _count_bind_by_platform((XBOX_PLATFORM,))


register_status(
    Image.open(_ICON).convert("RGBA"),
    "GTAOLUID",
    {
        "PC 绑定": get_pc_bind_num,
        "PS 绑定": get_ps_bind_num,
        "Xbox 绑定": get_xbox_bind_num,
    },
)
