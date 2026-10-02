"""插件本地静态资源的 HTTP 挂载与直链生成。"""

from pathlib import Path

from fastapi.staticfiles import StaticFiles

from gsuid_core.config import CONFIG_DEFAULT, core_config
from gsuid_core.app_life import app as fastapi_app

_UTILS_DIR = Path(__file__).resolve().parents[1]
_FONT_PATH = _UTILS_DIR / "fonts" / "youyuan.ttf"
_BG_PATH = _UTILS_DIR / "render" / "HTML" / "texture2d" / "infobg.jpg"
_ICON_PATH = _UTILS_DIR / "render" / "HTML" / "texture2d" / "gtaol.png"

_FONT_ROUTE = "/gtaoluid/fonts"
_BG_ROUTE = "/gtaoluid/texture2d"

_mounted = False


class _CORSStaticFiles(StaticFiles):
    """附带 CORS 头的静态资源；跨源取字体需要它。"""

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Access-Control-Allow-Origin"] = "*"
        return response


def _base_url() -> str:
    """gsuid_core 本地服务地址；绑定到全网卡时回落到回环地址。"""
    host = str(core_config.get_config("HOST") or CONFIG_DEFAULT["HOST"]).lower()
    port = str(core_config.get_config("PORT") or CONFIG_DEFAULT["PORT"])
    if host in ("", "all", "none", "dual", "0.0.0.0", "0.0.0.0:"):
        host = "127.0.0.1"
    return f"http://{host}:{port}"


def _ensure_mounted() -> None:
    """把字体与背景目录挂到核心 FastAPI，重复调用只挂一次。"""
    global _mounted
    if _mounted:
        return
    existing = {getattr(route, "path", None) for route in fastapi_app.routes}
    for route_path, directory, name in (
        (_FONT_ROUTE, _FONT_PATH.parent, "gtaoluid_fonts"),
        (_BG_ROUTE, _BG_PATH.parent, "gtaoluid_texture"),
    ):
        if route_path in existing or not directory.is_dir():
            continue
        fastapi_app.mount(route_path, _CORSStaticFiles(directory=directory), name=name)
    _mounted = True


def get_font_url() -> str:
    """本地字体直链；字体缺失时回退空串。"""
    if not _FONT_PATH.is_file():
        return ""
    _ensure_mounted()
    return f"{_base_url()}{_FONT_ROUTE}/{_FONT_PATH.name}"


def get_bg_url() -> str:
    """本地背景图直链；图片缺失时回退空串。"""
    if not _BG_PATH.is_file():
        return ""
    _ensure_mounted()
    return f"{_base_url()}{_BG_ROUTE}/{_BG_PATH.name}"


def get_icon_url() -> str:
    """本地插件标识图直链；图片缺失时回退空串。"""
    if not _ICON_PATH.is_file():
        return ""
    _ensure_mounted()
    return f"{_base_url()}{_BG_ROUTE}/{_ICON_PATH.name}"
