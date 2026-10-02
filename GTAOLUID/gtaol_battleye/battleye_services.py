"""GTAOL 战眼 [BattlEye] 封禁状态查询业务实现。"""

import base64
import random
import socket
import asyncio
import hashlib
from typing import Any, List, Tuple, Optional

from gsuid_core.logger import logger

from ..gtaol_config import GTAOLConfig
from ..utils.helpers.api import GTAOLApiError, get_status
from ..utils.database.models import GTAUser

# 战眼 UDP 查询固定超时，不随配置变化
BATTLEYE_TIMEOUT_SECONDS = 8

# 响应前 4 字节为回显，其余为封禁原因数据
_QUERY_HEADER_SIZE = 4


def _parse_rid(value: Any) -> Optional[int]:
    """严格解析 RID：仅接受正整数或纯数字字符串，其余回退 None。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            rid = int(text)
            return rid if rid > 0 else None
    return None


def _get_server_address() -> Tuple[str, int]:
    """解析 [战眼服务器地址] 配置；格式非法时抛出业务异常。"""
    raw = str(GTAOLConfig.get_config("BattlEyeServer").data).strip()
    host, sep, port_text = raw.rpartition(":")
    host = host.strip()
    port_text = port_text.strip()
    if not sep or not host or not port_text.isdigit():
        raise GTAOLApiError("战眼服务器地址配置有误，请检查 [战眼服务器地址] 配置项")

    port = int(port_text)
    if not 0 < port < 65536:
        raise GTAOLApiError("战眼服务器端口超出范围，请检查 [战眼服务器地址] 配置项")
    return host, port


def compute_be_id(rid: int) -> str:
    """由 Rockstar ID 计算战眼查询标识。"""
    rid_base64 = base64.b64encode(str(rid).encode("utf-8")).decode("ascii")
    return hashlib.md5(f"BE{rid_base64}".encode("ascii")).hexdigest().lower()


class _BattlEyeProtocol(asyncio.DatagramProtocol):
    """只接收一次 UDP 响应的最小协议实现。"""

    def __init__(self) -> None:
        self.transport: Optional[asyncio.DatagramTransport] = None
        self.response: Optional[bytes] = None
        self.future: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        if isinstance(transport, asyncio.DatagramTransport):
            self.transport = transport

    def datagram_received(self, data: bytes, addr: Any) -> None:
        if not self.future.done():
            self.response = data
            self.future.set_result(data)
        self._close()

    def error_received(self, exc: Exception) -> None:
        if not self.future.done():
            self.future.set_exception(exc)
        self._close()

    def connection_lost(self, exc: Optional[Exception]) -> None:
        if not self.future.done():
            if exc is not None:
                self.future.set_exception(exc)
            elif self.response is None:
                self.future.set_exception(asyncio.TimeoutError("未收到战眼服务器 UDP 响应"))
        self._close()

    def _close(self) -> None:
        if self.transport is not None and not self.transport.is_closing():
            self.transport.close()


async def query_ban_reason(rid: int, host: str, port: int) -> str:
    """向战眼服务器查询 RID 的封禁原因；返回空串表示未封禁。"""
    transport: Optional[asyncio.DatagramTransport] = None
    try:
        loop = asyncio.get_running_loop()
        protocol = _BattlEyeProtocol()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: protocol,
            family=socket.AF_INET,
            local_addr=("0.0.0.0", 0),
        )

        header = bytes(random.randint(0, 255) for _ in range(_QUERY_HEADER_SIZE))
        be_id = compute_be_id(rid)
        transport.sendto(header + be_id.encode("ascii"), (host, port))

        try:
            response = await asyncio.wait_for(protocol.future, timeout=BATTLEYE_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as e:
            raise GTAOLApiError(f"战眼服务器 [{host}:{port}] 响应超时，请稍后重试") from e
    finally:
        if transport is not None and not transport.is_closing():
            transport.close()

    if len(response) <= _QUERY_HEADER_SIZE:
        return ""

    try:
        return response[_QUERY_HEADER_SIZE:].decode("utf-8").strip()
    except UnicodeDecodeError as e:
        raise GTAOLApiError("战眼服务器返回数据解析失败，请稍后重试") from e


async def _resolve_rid_by_name(game_id: str) -> int:
    """显式昵称解析 RID：绑定表优先，未命中回退 HQSHI，HQSHI 失败即中止。"""
    bound_accounts: List[GTAUser] = await GTAUser.get_accounts_by_game_id(game_id)
    for account in bound_accounts:
        rid = _parse_rid(account.rockstar_id)
        if rid is not None:
            logger.info(f"[GTAOnline · 战眼查询] 绑定表命中 [{game_id}] 的 RID")
            return rid

    logger.info(f"[GTAOnline · 战眼查询] 绑定表未命中可用 RID，回退 HQSHI 查询 [{game_id}]")
    status_body = await get_status(game_id)
    rid = _parse_rid(status_body.get("rockstar_id"))
    if rid is None:
        raise GTAOLApiError(f"未获取到 [{game_id}] 的 RID，请稍后重试。")
    return rid


async def _resolve_main_account_rid(bot_id: str, user_id: str) -> Tuple[int, str]:
    """无参时取主账号 RID；本地取不到只提示刷新，不联网。"""
    main_acc = await GTAUser.get_main_account(user_id=user_id, bot_id=bot_id)
    if main_acc is None:
        raise GTAOLApiError("您尚未绑定GTAOL账户，请先使用 gta绑定 <游戏ID> 进行绑定。")

    rid = _parse_rid(main_acc.rockstar_id)
    if rid is None:
        raise GTAOLApiError(f"未获取到 [{main_acc.game_id}] 的 RID，请先使用 gta刷新数据 后重试。")
    return rid, main_acc.game_id


async def check_battleye_service(
    bot_id: str,
    user_id: str,
    identifier: Optional[str] = None,
) -> str:
    """查询玩家战眼封禁状态，返回可直接发送的文本结果。"""
    raw = identifier.strip() if identifier else ""
    target_name: Optional[str] = None

    rid = _parse_rid(raw) if raw else None
    if rid is None:
        if raw:
            rid = await _resolve_rid_by_name(raw)
            target_name = raw
        else:
            rid, target_name = await _resolve_main_account_rid(bot_id=bot_id, user_id=user_id)

    host, port = _get_server_address()
    logger.info(f"[GTAOnline · 战眼查询] 查询 RID [{rid}]，服务器 {host}:{port}")
    reason = await query_ban_reason(rid, host, port)

    lines = ["战眼封禁查询", f"RID：[{rid}]"]
    if target_name:
        lines.append(f"玩家：[{target_name}]")
    if reason:
        lines.append("状态：[已封禁]")
        lines.append(f"原因：[{reason}]")
    else:
        lines.append("状态：[未封禁]")
    return "\n".join(lines)
