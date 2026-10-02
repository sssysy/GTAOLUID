"""头像加载：远程 URL 转 data URI，失败回退本地默认头像。"""

import base64
from typing import Optional
from pathlib import Path

from ..downloader import download

_DEFAULT_AVATAR_PATH = Path(__file__).resolve().parents[1] / "render" / "HTML" / "texture2d" / "default_avatar.png"

_IMAGE_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF8", "image/gif"),
)


def _guess_mime(data: bytes) -> str:
    """按文件头判定图片类型；无法识别时回退 image/jpeg。"""
    for magic, mime in _IMAGE_MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _to_data_uri(data: bytes) -> str:
    """把图片字节转成 data URI；空数据返回空串。"""
    if not data:
        return ""
    return f"data:{_guess_mime(data)};base64,{base64.b64encode(data).decode('ascii')}"


async def load_avatar_data_uri(url: Optional[str]) -> str:
    """下载头像并转 data URI；URL 缺失或下载失败时回退本地默认头像。"""
    target = (url or "").strip()
    if target:
        downloaded = await download(target)
        if downloaded and downloaded.is_file() and downloaded.stat().st_size > 0:
            return _to_data_uri(downloaded.read_bytes())

    if _DEFAULT_AVATAR_PATH.is_file() and _DEFAULT_AVATAR_PATH.stat().st_size > 0:
        return _to_data_uri(_DEFAULT_AVATAR_PATH.read_bytes())

    return ""
