"""GTAOL 差事筛选词表与官方中文映射。

词表是筛选解析的唯一数据源：人话 -> 接口取值。未收录的写法一律不识别。
"""

# 时间范围
DATE_RANGE_MAP: dict[str, str] = {
    "上周": "last7",
    "上个月": "lastmonth",
    "去年": "lastyear",
}
DEFAULT_DATE_RANGE = "any"

# 差事来源
SOURCE_MAP: dict[str, str] = {
    "官方": "rockstar",
    "认证": "rockstarVerified",
    "社区": "community",
    "个人": "scMembers",
}

# 排序
SORT_MAP: dict[str, str] = {
    "热门": "likes",
    "最新": "createdDate",
}
DEFAULT_SORT = "likes"

# 差事主类型
MISSION_TYPE_MAP: dict[str, str] = {
    "任务": "mission",
    "死斗游戏": "deathmatch",
    "占山为王": "kingofthehill",
    "竞速": "race",
    "生存战": "survival",
    "夺取": "capture",
    "团队生存游戏": "lastteamstanding",
    "跳伞": "parachuting",
}

# 差事子类型
SUBTYPE_MAP: dict[str, tuple[str, str]] = {
    "制作器任务": ("mission", "creator"),
    "对抗模式": ("mission", "adversary"),
    "团队死斗游戏": ("deathmatch", "teamdeathmatch"),
    "载具死斗游戏": ("deathmatch", "vehicledeathmatch"),
    "竞技场死斗": ("deathmatch", "arenadeathmatch"),
    "团队占山为王": ("kingofthehill", "teamkingofthehill"),
    "追逐竞速": ("race", "pursuitrace"),
    "街头竞速": ("race", "streetrace"),
    "阿浩特别工坊竞速": ("race", "haospecialworksrace"),
    "开轮式竞速": ("race", "openwheelrace"),
    "竞技场之战": ("race", "arenawar"),
    "幻变竞速": ("race", "transformrace"),
    "特殊载具竞速": ("race", "specialrace"),
    "特技竞速": ("race", "stuntrace"),
    "射击竞赛": ("race", "targetrace"),
    "空中竞速": ("race", "airrace"),
    "两轮车竞速": ("race", "bikerace"),
    "陆地竞速": ("race", "landrace"),
    "水上竞速": ("race", "waterrace"),
    "漂移竞速": ("race", "driftrace"),
    "直线竞速": ("race", "dragrace"),
}

# 差事模式
MODE_NAME_MAP: dict[str, str] = {
    "MISSION": "任务",
    "RANDOMMISSION": "随机任务",
    "CONTACTMISSION": "联系人任务",
    "MISSIONCREATOR": "制作器任务",
    "CAPTURE": "夺取",
    "LASTTEAMSTANDING": "团队生存游戏",
    "HEIST": "抢劫任务",
    "HEISTPREP": "抢劫前置任务",
    "ADVERSARYMODE": "对抗模式",
    "RACE": "竞速",
    "AIRRACE": "空中竞速",
    "BIKERACE": "两轮车竞速",
    "LANDRACE": "陆地竞速",
    "PARACHUTING": "跳伞",
    "WATERRACE": "水上竞速",
    "STUNTRACE": "特技竞速",
    "SPECIALRACE": "特殊载具竞速",
    "TRANSFORMRACE": "幻变竞速",
    "FOOTRACE": "徒步竞速",
    "TARGETRACE": "射击竞赛",
    "ARENAWAR": "竞技场之战",
    "OPENWHEELRACE": "开轮式竞速",
    "PURSUITRACE": "追逐竞速",
    "STREETRACE": "街头竞速",
    "HAOSPECIALWORKSRACE": "阿浩特别工坊竞速",
    "DRIFTRACE": "漂移竞速",
    "DRAGRACE": "直线竞速",
    "DEATHMATCH": "死斗游戏",
    "TEAMDEATHMATCH": "团队死斗游戏",
    "VEHICLEDEATHMATCH": "载具死斗游戏",
    "ARENADEATHMATCH": "竞技场死斗",
    "SURVIVAL": "生存战",
    "KINGOFTHEHILL": "占山为王",
    "TEAMKINGOFTHEHILL": "团队占山为王",
    "UNKNOWN": "未知",
}

# 载具类别
VEHICLE_CLASS_MAP: dict[str, str] = {
    "Boats": "船",
    "Compacts": "小型汽车",
    "Coupes": "轿跑车",
    "Cycles": "自行车",
    "Helicopters": "直升机",
    "Industrial": "工业用车",
    "Motorcycles": "摩托车",
    "Bikes": "摩托车",
    "Muscle": "肌肉车",
    "OffRoad": "越野车",
    "Planes": "飞机",
    "Sedans": "轿车",
    "Special": "特种车",
    "Sports": "跑车",
    "SportsClassics": "经典跑车",
    "Super": "超级跑车",
    "SUVs": "SUV",
    "Utility": "公共事业用车",
    "Vans": "厢型车",
    "Weaponised": "武装车",
    "Unknown": "未知",
}
