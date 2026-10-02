"""GTAOL 玩家信息业务编排层。"""

import base64
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path

from gsuid_core.logger import logger

from ..utils.downloader import download
from ..utils.database.models import GTAUser
from ..utils.render.HTML.render import render_detail_card, render_summary_card
from ..utils.helpers.player_data import get_latest_player_snapshot

# 接口自带的元数据/审核字段，详情不展示
_META_KEYS = {
    "索引",
    "状态",
    "数据版本",
    "备注",
    "规则版本",
    "重载",
    "分析",
    "异常",
    "存疑",
    "标记",
    "审查值",
}

# 详情数据列排除集合：元数据与奖章/成就/升级进度均另有安排
_DETAIL_EXCLUDED_KEYS = _META_KEYS | {"奖章", "成就", "升级进度"}

# 顶部身份信息占用的字段，从数据列中摘除避免重复
_HEADER_KEYS = {
    "昵称",
    "rockstar_id",
    "头像",
    "平台名称",
    "等级",
    "现金",
    "银行",
    "帮会缩写",
    "帮会颜色",
    "GTA 在线模式中花费的时间",
}


def _parse_money(val: Any) -> float:
    """安全解析金额字符串或数值，异常与缺失统一回退为 0.0。"""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace("$", "").replace(",", "")
    if not s:
        return 0.0
    mult = 1.0
    if s.endswith(("M", "m")):
        mult = 1_000_000.0
        s = s[:-1]
    elif s.endswith(("K", "k")):
        mult = 1_000.0
        s = s[:-1]
    elif s.endswith(("B", "b")):
        mult = 1_000_000_000.0
        s = s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


def _is_empty_value(val: Any) -> bool:
    """判断接口空值；空串与字面量 None/null 同样视为无数据。"""
    if val is None:
        return True
    if isinstance(val, str):
        return val.strip() in ("", "None", "null")
    if isinstance(val, (list, dict)):
        return len(val) == 0
    return False


def _parse_int(val: Any) -> int:
    """按整数字面量解析（允许千分位逗号）；缺失或不可解析统一回退为 0。"""
    if isinstance(val, bool):
        return 0
    if isinstance(val, int):
        return val
    if isinstance(val, float):
        return int(val)
    if isinstance(val, str):
        try:
            return int(val.strip().replace(",", ""))
        except ValueError:
            return 0
    return 0


def _build_detail_node(label: str, value: Any) -> Optional[Dict[str, Any]]:
    """构造单个详情节点；空值返回 None，嵌套结构落在 children 上。"""
    if _is_empty_value(value):
        return None
    if isinstance(value, (dict, list)):
        children: List[Dict[str, Any]] = []
        source = value.items() if isinstance(value, dict) else enumerate(value, start=1)
        for key, sub in source:
            sub_label = str(key) if isinstance(value, dict) else f"#{key}"
            child = _build_detail_node(sub_label, sub)
            if child is not None:
                children.append(child)
        if not children:
            return None
        return {"label": label, "children": children}
    return {"label": label, "value": str(value)}


def _build_detail_tree(body: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把快照 body 转成详情树，保留接口原始顺序并隐藏空值。"""
    tree: List[Dict[str, Any]] = []
    for key, value in body.items():
        if key in _DETAIL_EXCLUDED_KEYS or key in _HEADER_KEYS:
            continue
        node = _build_detail_node(str(key), value)
        if node is not None:
            tree.append(node)
    return tree


async def _assemble_identity(game_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
    """组装总览与详情共用的玩家身份头部，缺失字段严格回退为 0 或 None。"""
    nickname = body.get("昵称") or game_id
    crew_tag = body.get("帮会缩写") or ""
    crew_color = body.get("帮会颜色") or ""
    rank = body.get("等级") or 0
    platform_name = body.get("平台名称") or "None"
    rid = body.get("rockstar_id") or "None"
    time_played = body.get("GTA 在线模式中花费的时间") or "0"

    raw_cash = body.get("现金", 0)
    raw_bank = body.get("银行", 0)
    cash_num = int(raw_cash) if isinstance(raw_cash, (int, float)) else int(_parse_money(raw_cash))
    bank_num = int(raw_bank) if isinstance(raw_bank, (int, float)) else int(_parse_money(raw_bank))

    avatar_src = ""
    avatar_url = body.get("头像")
    if avatar_url and isinstance(avatar_url, str) and avatar_url.strip():
        downloaded = await download(avatar_url.strip())
        if downloaded and downloaded.is_file() and downloaded.stat().st_size > 0:
            mime = "image/png" if downloaded.suffix.lower() == ".png" else "image/jpeg"
            b64_data = base64.b64encode(downloaded.read_bytes()).decode("ascii")
            avatar_src = f"data:{mime};base64,{b64_data}"

    return {
        "nickname": nickname,
        "crew_tag": crew_tag,
        "crew_color": crew_color,
        "rank": rank,
        "platform_name": platform_name,
        "rid": rid,
        "time_played": time_played,
        "cash_str": f"{cash_num:,}",
        "bank_str": f"{bank_num:,}",
        "cash_num": cash_num,
        "bank_num": bank_num,
        "avatar_src": avatar_src,
    }


async def _assemble_overview_data(game_id: str, raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """清洗快照原始数据并组装为供渲染层消费的纯结构化字典。

    所有缺失或异常字段严格回退为 0 或 None，严禁填入任何测试假数据。
    """
    d: Dict[str, Any] = raw_data.get("body", raw_data)
    identity = await _assemble_identity(game_id, d)

    # 1. 资金收入与支出明细
    in_jobs = _parse_money(d.get("差事收入", 0))
    in_reward = _parse_money(d.get("表现良好奖励收入", 0))
    in_bet = _parse_money(d.get("赌博收入", 0))
    in_car = _parse_money(d.get("出售载具收入", 0))
    in_total = _parse_money(d.get("总收入", 0))

    income_items: List[Dict[str, Any]] = []
    if in_jobs > 0:
        income_items.append({"name": "差事收入", "value": in_jobs, "color": "#f39c12"})
    if in_reward > 0:
        income_items.append({"name": "良好奖励", "value": in_reward, "color": "#2ecc71"})
    if in_bet > 0:
        income_items.append({"name": "赌博下注", "value": in_bet, "color": "#f1c40f"})
    if in_car > 0:
        income_items.append({"name": "出售载具", "value": in_car, "color": "#3498db"})

    tracked_in = in_jobs + in_reward + in_bet + in_car
    if in_total > tracked_in:
        diff_in = in_total - tracked_in
        income_items.append({"name": "未记录收入", "value": diff_in, "color": "#95a5a6"})

    ex_prop = _parse_money(d.get("房产和公用事业花费", 0))
    ex_veh = _parse_money(d.get("载具和维护花费", 0))
    ex_job = _parse_money(d.get("差事和活动入场花费", 0))
    ex_wpn = _parse_money(d.get("武器和护甲花费", 0))
    ex_ent = _parse_money(d.get("风格和娱乐花费", 0))
    ex_med = _parse_money(d.get("医疗花费", 0))
    ex_total = _parse_money(d.get("总花费", 0))

    expense_items: List[Dict[str, Any]] = []
    if ex_prop > 0:
        expense_items.append({"name": "房产公用", "value": ex_prop, "color": "#9b59b6"})
    if ex_veh > 0:
        expense_items.append({"name": "载具维护", "value": ex_veh, "color": "#e74c3c"})
    if ex_job > 0:
        expense_items.append({"name": "差事活动", "value": ex_job, "color": "#f39c12"})
    if ex_wpn > 0:
        expense_items.append({"name": "武器护甲", "value": ex_wpn, "color": "#e67e22"})
    if ex_ent > 0:
        expense_items.append({"name": "风格娱乐", "value": ex_ent, "color": "#fd79a8"})
    if ex_med > 0:
        expense_items.append({"name": "医疗联络", "value": ex_med, "color": "#1abc9c"})

    cur_balance = float(identity["cash_num"] + identity["bank_num"])
    if cur_balance > 0:
        expense_items.append({"name": "当前结余", "value": cur_balance, "color": "#2ecc71"})

    # 3. 角色体能属性
    skills = [
        {"name": "体力", "value": d.get("体力") or "0%", "is_mental": False},
        {"name": "射击", "value": d.get("射击") or "0%", "is_mental": False},
        {"name": "力量", "value": d.get("力量") or "0%", "is_mental": False},
        {"name": "潜行", "value": d.get("潜行") or "0%", "is_mental": False},
        {"name": "飞行", "value": d.get("飞行") or "0%", "is_mental": False},
        {"name": "驾驶", "value": d.get("驾驶") or "0%", "is_mental": False},
        {"name": "肺活量", "value": d.get("肺活量") or "0%", "is_mental": False},
        {"name": "精神状态", "value": d.get("精神状态") or "0%", "is_mental": True},
    ]

    # 4. 战斗与武器
    kd = d.get("竞赛玩家击杀/死亡比率") or "0.00"
    p_kills = d.get("杀死的玩家总数") or 0
    p_deaths = d.get("被其他玩家杀死的总次数") or 0
    npc_kills = d.get("击杀数") or 0
    hs_kills = d.get("爆头击杀数") or 0
    accuracy = d.get("精准度") or "0%"

    combat_items = [
        {"label": "玩家 KD 比率", "val": str(kd), "color_cls": "val-gold"},
        {"label": "玩家击杀 / 被杀", "val": f"{p_kills} / {p_deaths}", "color_cls": ""},
        {"label": "NPC 击杀总数", "val": str(npc_kills), "color_cls": ""},
        {"label": "爆头率 / 命中精度", "val": f"{hs_kills} ({accuracy})", "color_cls": ""},
    ]

    fav_w = d.get("最喜欢的武器")
    if not isinstance(fav_w, dict):
        fav_w = {}
    favorite_weapon = {
        "name": fav_w.get("名称") or "None",
        "kills": str(fav_w.get("击杀数") or "0"),
        "headshots": str(fav_w.get("爆头击杀数") or "0"),
        "accuracy": str(fav_w.get("精准度") or "0%"),
    }

    # 5. 载具行驶
    vehicle_items = [
        {"label": "陆上最高车速", "val": str(d.get("驾驶陆上载具达到的最高速度") or "0"), "color_cls": "val-gold"},
        {"label": "最快载具", "val": str(d.get("驾驶过最快的陆上载具") or "None"), "color_cls": ""},
        {"label": "旅行总里程", "val": str(d.get("旅行距离") or "0"), "color_cls": ""},
        {"label": "驾驶总用时", "val": str(d.get("汽车驾驶时间") or "0"), "color_cls": ""},
        {
            "label": "炸毁汽车 / 直升机",
            "val": f"{d.get('炸毁汽车数') or 0} / {d.get('炸毁直升机数') or 0}",
            "color_cls": "",
        },
        {
            "label": "撞车 / 有惊无险",
            "val": f"{d.get('撞车次数') or '0'} / {d.get('有惊无险次数') or '0'}",
            "color_cls": "",
        },
    ]

    # 6. 犯罪通缉
    wanted_items = [
        {"label": "被通缉总次数", "val": f"{d.get('被通缉次数') or '0'} 次", "color_cls": ""},
        {
            "label": "获得 / 逃脱星级",
            "val": f"{d.get('获得的通缉星级总数') or '0'} / {d.get('逃脱通缉星级总数') or '0'}",
            "color_cls": "",
        },
        {"label": "5星通缉生存时长", "val": str(d.get("5 星通缉等级持续时间") or "0"), "color_cls": ""},
        {"label": "通缉总时长", "val": str(d.get("被通缉的时间") or "0"), "color_cls": ""},
        {
            "label": "击杀警察 / 特工",
            "val": f"{d.get('击杀警察数') or '0'} / {d.get('击杀国安局特工数') or '0'}",
            "color_cls": "",
        },
        {"label": "抢劫商店次数", "val": f"{d.get('抢劫商店次数') or '0'} 次", "color_cls": ""},
    ]

    # 7. 竞技活动
    comp = d.get("竞赛统计数据")
    if not isinstance(comp, dict):
        comp = {}
    race = comp.get("竞速")
    if not isinstance(race, dict):
        race = {}
    race_win = race.get("赢") or "0"
    race_loss = race.get("输") or "0"
    race_time = race.get("竞速时间") or "0"

    minigames = ["死斗游戏", "网球", "高尔夫", "跳伞", "飞镖游戏"]
    best_game = None
    best_played = -1
    for gname in minigames:
        gdata = comp.get(gname, {})
        if not isinstance(gdata, dict):
            continue
        wins = _parse_int(gdata.get("赢"))
        losses = _parse_int(gdata.get("输"))
        total = wins + losses
        if total > best_played:
            best_played = total
            best_game = (gname, wins, losses, gdata)

    if best_game and best_played > 0:
        gname, wins, losses, gdata = best_game
        extras = [(k, v) for k, v in gdata.items() if k not in ("赢", "输")]
        extra_str = f" ({extras[0][0]} {extras[0][1]})" if extras else ""
        minigame_lbl = f"{gname}胜负"
        minigame_val = f"{wins} 胜 {losses} 负{extra_str}"
    else:
        minigame_lbl = "小游戏胜负"
        minigame_val = "None"

    comp_items = [
        {"label": "竞速胜负场", "val": f"{race_win} 胜 {race_loss} 负", "color_cls": "val-green"},
        {"label": "竞速花费时间", "val": str(race_time), "color_cls": ""},
        {"label": "最高生存战波数", "val": f"第 {d.get('达到的最高生存战波数') or '0'} 波", "color_cls": ""},
        {"label": minigame_lbl, "val": minigame_val, "color_cls": ""},
        {"label": "单人最长战局", "val": str(d.get("持续时间最长单人游戏战局") or "0"), "color_cls": ""},
        {"label": "每场战局均时", "val": str(d.get("每场战局平均用时") or "0"), "color_cls": ""},
    ]

    # 8. 奖章成就
    medals = d.get("奖章")
    if not isinstance(medals, dict):
        medals = {}
    completed_plat = [k for k, v in medals.items() if isinstance(v, dict) and v.get("完成") == "是"]
    plat_count = len(completed_plat)
    total_medals = len(medals)

    priority_pool = [
        ("佩里科岛抢劫任务", "佩里科岛抢劫"),
        ("别惹德瑞", "名人合约 (德瑞)"),
        ("拯救世界", "末日抢劫"),
        ("联合储蓄合约", "联合储蓄合约"),
        ("名钻赌场抢劫", "名钻豪劫"),
        ("亡命逃犯", "5星通缉生存"),
        ("炸翻天", "爆炸破坏专家"),
        ("车手", "竞速老手"),
        ("堂主", "竞技场之王"),
    ]

    highlights: List[Dict[str, str]] = []
    for medal_key, display_name in priority_pool:
        medal_item = medals.get(medal_key)
        if isinstance(medal_item, dict) and medal_item.get("完成") == "是":
            highlights.append({"name": display_name, "status": "铂金完成", "color_cls": "val-green"})
            if len(highlights) >= 3:
                break

    if len(highlights) < 3:
        for k in completed_plat:
            if k not in [p[0] for p in priority_pool]:
                highlights.append({"name": k, "status": "铂金完成", "color_cls": "val-green"})
                if len(highlights) >= 3:
                    break

    if len(highlights) < 3:
        in_prog = []
        for k, v in medals.items():
            if not isinstance(v, dict) or v.get("完成") == "是":
                continue
            cur = _parse_int(v.get("当前"))
            tgt = _parse_int(v.get("目标"))
            if cur > 0 and tgt > 0:
                in_prog.append((k, f"{v.get('当前')}/{v.get('目标')}", cur / tgt))
        in_prog.sort(key=lambda x: x[2], reverse=True)
        for k, prog_str, _ in in_prog:
            highlights.append({"name": k, "status": f"进行中 {prog_str}", "color_cls": "val-gold"})
            if len(highlights) >= 3:
                break

    medals_summary = {
        "plat_count": plat_count,
        "total_medals": total_medals,
        "highlights": highlights,
        "recent_activity": str(d.get("最近的活动") or "None"),
    }

    return {
        **identity,
        "income_items": income_items,
        "income_total": in_total,
        "expense_items": expense_items,
        "expense_total": ex_total,
        "skills": skills,
        "combat_items": combat_items,
        "favorite_weapon": favorite_weapon,
        "vehicle_items": vehicle_items,
        "wanted_items": wanted_items,
        "comp_items": comp_items,
        "medals_summary": medals_summary,
    }


async def _resolve_snapshot(
    bot_id: str,
    user_id: str,
    target_game_id: Optional[str],
) -> Tuple[Optional[str], Optional[Tuple[Path, Dict[str, Any]]], str]:
    """解析目标游戏ID并读取本地最新快照，返回 (game_id, 快照, 提示消息)。"""
    game_id = target_game_id.strip() if target_game_id and target_game_id.strip() else None
    if not game_id:
        main_acc = await GTAUser.get_main_account(user_id=user_id, bot_id=bot_id)
        if main_acc is None:
            return None, None, "您尚未绑定GTAOL账户，请先使用 gta绑定 <游戏ID> 进行绑定。"
        game_id = main_acc.game_id

    local_res = get_latest_player_snapshot(game_id)
    if not local_res:
        return game_id, None, f"未找到 [{game_id}] 的本地数据，请先使用 gta刷新数据 拉取最新数据！"
    return game_id, local_res, "OK"


async def render_overview_service(
    bot_id: str,
    user_id: str,
    target_game_id: Optional[str] = None,
) -> Tuple[Optional[bytes], str]:
    """生成 GTA 在线模式玩家模块化总览图片。

    Returns:
        Tuple[Optional[bytes], str]: (渲染图片字节流, 提示或错误消息)
    """
    game_id, local_res, msg = await _resolve_snapshot(bot_id, user_id, target_game_id)
    if local_res is None:
        return None, msg
    snapshot_file, raw_data = local_res
    logger.info(f"[GTAOnline · 数据总览] 开始为 {game_id} 组装数据，数据源: {snapshot_file.name}")

    try:
        overview_data = await _assemble_overview_data(game_id, raw_data)
        img_bytes = await render_summary_card(overview_data)
        return img_bytes, "OK"
    except Exception as e:
        logger.exception(f"[GTAOnline · 数据总览] 渲染总览卡片异常: {e}")
        return None, "渲染总览图片失败，请稍后重试。"


async def render_detail_service(
    bot_id: str,
    user_id: str,
    target_game_id: Optional[str] = None,
) -> Tuple[Optional[bytes], str]:
    """生成玩家全量字段详情图片。

    Returns:
        Tuple[Optional[bytes], str]: (渲染图片字节流, 提示或错误消息)
    """
    game_id, local_res, msg = await _resolve_snapshot(bot_id, user_id, target_game_id)
    if local_res is None:
        return None, msg

    snapshot_file, raw_data = local_res
    logger.info(f"[GTAOnline · 玩家详情] 开始为 {game_id} 组装数据，数据源: {snapshot_file.name}")

    try:
        body = raw_data.get("body", raw_data)
        if not isinstance(body, dict):
            return None, f"未找到 [{game_id}] 可展示的玩家详情数据。"
        tree = _build_detail_tree(body)
        if not tree:
            return None, f"未找到 [{game_id}] 可展示的玩家详情数据。"
        header = await _assemble_identity(game_id, body)
        img_bytes = await render_detail_card(header, tree)
        return img_bytes, "OK"
    except Exception as e:
        logger.exception(f"[GTAOnline · 玩家详情] 渲染详情卡片异常: {e}")
        return None, "渲染详情图片失败，请稍后重试。"
