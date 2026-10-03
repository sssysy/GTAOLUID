from typing import Any, Dict, List, Type, Tuple, TypeVar, Optional

from sqlmodel import Field, select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from gsuid_core.logger import logger
from gsuid_core.utils.database.startup import exec_list
from gsuid_core.utils.database.base_models import BaseIDModel, with_session

T_GTAUser = TypeVar("T_GTAUser", bound="GTAUser")


class GTAUser(BaseIDModel, table=True):
    __table_args__: Dict[str, Any] = {"extend_existing": True}

    user_id: str = Field(default="", index=True, title="用户ID")
    bot_id: str = Field(default="onebot", title="Bot平台")
    game_id: str = Field(default="", index=True, title="Rockstar游戏昵称")
    platform: str = Field(default="0", title="平台代码")
    is_main: bool = Field(default=False, title="是否主账号")
    rockstar_id: str = Field(default="", title="Rockstar数字ID")
    avatar_url: str = Field(default="", title="Rockstar头像URL")

    @classmethod
    @with_session
    async def bind_account(
        cls: Type[T_GTAUser],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
        game_id: str,
        platform: str,
    ) -> Tuple[T_GTAUser, bool]:
        """绑定账号。若已存在该 game_id 则覆盖更新平台，否则新建绑定。

        Returns:
            Tuple[GTAUser, bool]: (用户记录, 是否为覆盖更新)
        """
        stmt = select(cls).where(
            cls.user_id == user_id,
            cls.bot_id == bot_id,
            func.lower(cls.game_id) == game_id.lower(),
        )
        result = await session.execute(stmt)
        existing = result.scalars().first()

        if existing is not None:
            existing.platform = platform
            existing.game_id = game_id
            session.add(existing)
            logger.info(f"[GTAOnline · 账户绑定] 覆盖更新绑定 {user_id} -> {game_id} 平台: {platform}")
            return existing, True

        # 查询是否为用户绑定的首个账号
        user_stmt = select(cls).where(cls.user_id == user_id, cls.bot_id == bot_id)
        user_result = await session.execute(user_stmt)
        has_any = user_result.scalars().first() is not None

        is_main = not has_any
        new_account = cls(
            user_id=user_id,
            bot_id=bot_id,
            game_id=game_id,
            platform=platform,
            is_main=is_main,
        )
        session.add(new_account)
        logger.info(f"[GTAOnline · 账户绑定] 新增绑定 {user_id} -> {game_id} (主账号: {is_main}, 平台: {platform})")
        return new_account, False

    @classmethod
    @with_session
    async def unbind_account(
        cls: Type[T_GTAUser],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
        game_id: Optional[str] = None,
    ) -> Tuple[int, Optional[str], Optional[str]]:
        """解绑账号。未传 game_id 时解绑主账号；若删除的是主账号则顺位继承。

        Returns:
            Tuple[int, Optional[str], Optional[str]]:
                - 状态码：0 成功, -1 用户无绑定, -2 指定 game_id 未找到
                - 被删除的账号名
                - 顺位晋升为新主账号的账号名（若无则为 None）
        """
        if game_id and game_id.strip():
            stmt = select(cls).where(
                cls.user_id == user_id,
                cls.bot_id == bot_id,
                func.lower(cls.game_id) == game_id.strip().lower(),
            )
            result = await session.execute(stmt)
            target = result.scalars().first()
            if target is None:
                return -2, None, None
        else:
            stmt = select(cls).where(
                cls.user_id == user_id,
                cls.bot_id == bot_id,
                cls.is_main == True,  # noqa: E712
            )
            result = await session.execute(stmt)
            target = result.scalars().first()
            if target is None:
                return -1, None, None

        deleted_name = target.game_id
        was_main = target.is_main
        await session.delete(target)
        await session.flush()

        new_main_name: Optional[str] = None
        if was_main:
            # 顺位将剩下的第一个账号设为主账号
            remain_stmt = (
                select(cls).where(cls.user_id == user_id, cls.bot_id == bot_id).order_by(cls.id.asc())  # type: ignore
            )
            remain_result = await session.execute(remain_stmt)
            remaining_first = remain_result.scalars().first()
            if remaining_first is not None:
                remaining_first.is_main = True
                session.add(remaining_first)
                new_main_name = remaining_first.game_id
                logger.info(f"[GTAOnline · 账户绑定] 主账号已解绑，顺位提升新主账号: {new_main_name}")

        return 0, deleted_name, new_main_name

    @classmethod
    @with_session
    async def get_main_account(
        cls: Type[T_GTAUser],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
    ) -> Optional[T_GTAUser]:
        """获取用户当前主账号。"""
        stmt = select(cls).where(
            cls.user_id == user_id,
            cls.bot_id == bot_id,
            cls.is_main == True,  # noqa: E712
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    @classmethod
    @with_session
    async def get_user_accounts(
        cls: Type[T_GTAUser],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
    ) -> List[T_GTAUser]:
        """获取用户绑定的所有账号列表。"""
        stmt = (
            select(cls).where(cls.user_id == user_id, cls.bot_id == bot_id).order_by(cls.id.asc())  # type: ignore
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return list(rows) if rows else []

    @classmethod
    @with_session
    async def get_accounts_by_game_id(
        cls: Type[T_GTAUser],
        session: AsyncSession,
        game_id: str,
    ) -> List[T_GTAUser]:
        """按游戏昵称全局查找绑定记录，不区分用户，按绑定先后排序。"""
        stmt = (
            select(cls).where(func.lower(cls.game_id) == game_id.strip().lower()).order_by(cls.id.asc())  # type: ignore
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return list(rows) if rows else []

    @classmethod
    @with_session
    async def update_account_profile(
        cls: Type[T_GTAUser],
        session: AsyncSession,
        user_id: str,
        bot_id: str,
        game_id: str,
        rockstar_id: str,
        avatar_url: str,
    ) -> Optional[T_GTAUser]:
        """把 Rockstar 资料写入对应绑定记录；绑定不存在时返回 None。"""
        stmt = select(cls).where(
            cls.user_id == user_id,
            cls.bot_id == bot_id,
            func.lower(cls.game_id) == game_id.lower(),
        )
        result = await session.execute(stmt)
        existing = result.scalars().first()
        if existing is None:
            logger.warning(f"[GTAOnline · 账户绑定] 未找到绑定记录 {user_id} -> {game_id}，资料未写入")
            return None

        existing.rockstar_id = rockstar_id
        existing.avatar_url = avatar_url
        session.add(existing)
        return existing


# 老库补列：核心在 WS 启动前统一执行 exec_list 中的语句
exec_list.extend(
    [
        "ALTER TABLE gtauser ADD COLUMN rockstar_id TEXT DEFAULT '';",
        "ALTER TABLE gtauser ADD COLUMN avatar_url TEXT DEFAULT '';",
    ]
)
