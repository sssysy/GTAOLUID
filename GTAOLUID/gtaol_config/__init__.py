"""GTAOLUID 插件配置项定义与注册。"""

from gsuid_core.data_store import get_res_path
from gsuid_core.utils.plugins_config.models import GSC, GsIntConfig, GsStrConfig
from gsuid_core.utils.plugins_config.gs_config import StringConfig

CONFIG_PATH = get_res_path("GTAOLUID") / "config.json"

CONFIG_DEFAULT: dict[str, GSC] = {
    "CacheCleanDays": GsIntConfig(
        "缓存自动清理时间 (天)",
        "缓存文件保留天数，超过该天数的缓存将被自动清理；0 表示不自动清理",
        3,
    ),
    "BattlEyeServer": GsStrConfig(
        "战眼服务器地址",
        "用于战眼查询的 UDP 服务器地址",
        "51.89.97.102:61455",
    ),
}

GTAOLConfig = StringConfig("GTAOLUID", CONFIG_PATH, CONFIG_DEFAULT)
