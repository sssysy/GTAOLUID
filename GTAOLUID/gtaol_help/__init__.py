"""GTAOL 帮助命令与帮助图渲染。"""

import json
from pathlib import Path

from PIL import Image

from gsuid_core.sv import SV, get_plugin_available_prefix
from gsuid_core.bot import Bot
from gsuid_core.logger import logger
from gsuid_core.models import Event
from gsuid_core.help.model import PluginHelp
from gsuid_core.help.utils import register_help
from gsuid_core.help.draw_new_plugin_help import get_new_help

from ..version import GTAOLUID_version

PLUGIN_NAME = "GTAOLUID"
PLUGIN_PREFIX = get_plugin_available_prefix(PLUGIN_NAME)

CURRENT_DIR = Path(__file__).parent
ICON = CURRENT_DIR.parent.parent / "ICON.png"
HELP_DATA = CURRENT_DIR / "help.json"
TEXT_PATH = CURRENT_DIR / "texture2d"
ICON_PATH = CURRENT_DIR / "icon_path"

sv_gtaol_help = SV("GTAOL帮助")


def _load_help_data() -> dict[str, PluginHelp]:
    """读取 help.json 中的帮助条目。"""
    with open(HELP_DATA, "r", encoding="utf-8") as file:
        return json.load(file)


async def _render_help(pm: int) -> bytes:
    """渲染 GTAOL 帮助图并返回图片字节。"""
    return await get_new_help(
        plugin_name=PLUGIN_NAME,
        plugin_info={f"v{GTAOLUID_version}": ""},
        plugin_icon=Image.open(ICON),
        plugin_help=_load_help_data(),
        plugin_prefix=PLUGIN_PREFIX,
        help_mode="dark",
        banner_bg=Image.open(TEXT_PATH / "banner_bg.jpg"),
        banner_sub_text="你每天会忘记的事情上千件，那么为何不忘记这件事呢？",
        help_bg=Image.open(TEXT_PATH / "bg.jpg"),
        cag_bg=Image.open(TEXT_PATH / "cag_bg.png"),
        item_bg=Image.open(TEXT_PATH / "item.png"),
        icon_path=ICON_PATH,
        footer=Image.open(TEXT_PATH / "footer.png"),
        enable_cache=True,
        column=3,
        pm=pm,
    )


@sv_gtaol_help.on_fullmatch("帮助", block=True)
async def gtaol_help(bot: Bot, ev: Event) -> None:
    try:
        await bot.send(await _render_help(ev.user_pm))
    except Exception as e:
        logger.exception(f"[GTAOnline · 帮助] 帮助图渲染异常: {e}")
        await bot.send("运行出错，帮助图生成失败，请稍后重试。")


register_help(PLUGIN_NAME, f"{PLUGIN_PREFIX}帮助", Image.open(ICON))
