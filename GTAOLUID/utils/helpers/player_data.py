import json
from typing import Any, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime

from gsuid_core.logger import logger
from gsuid_core.data_store import get_res_path

PLAYER_DATA_DIR: Path = get_res_path("GTAOLUID") / "playerdata"
PLAYER_DATA_DIR.mkdir(parents=True, exist_ok=True)


def parse_snapshot_timestamp(snapshot: Dict[str, Any]) -> int:
    """从快照 JSON 中提取生成时间并转换为秒级 Unix 时间戳；缺失或不可解析回退为 0。"""
    body = snapshot.get("body", snapshot)
    time_str = body.get("时间")
    if isinstance(time_str, str) and time_str.strip():
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
            try:
                dt = datetime.strptime(time_str.strip(), fmt)
                return int(dt.timestamp())
            except ValueError:
                continue

    return 0


def save_player_snapshot(
    game_id: str,
    snapshot_id: str,
    snapshot_data: Dict[str, Any],
) -> Path:
    """将快照数据保存为标准命名格式：{玩家名}_{快照id}_{生成时间戳}.json。"""
    PLAYER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = parse_snapshot_timestamp(snapshot_data)
    file_name = f"{game_id}_{snapshot_id}_{ts}.json"
    file_path = PLAYER_DATA_DIR / file_name

    file_path.write_text(
        json.dumps(snapshot_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"[GTAOnline · 数据存储] 写入快照文件: {file_name}")
    return file_path


def get_latest_player_snapshot(
    game_id: str,
) -> Optional[Tuple[Path, Dict[str, Any]]]:
    """读取本地最新的一份玩家快照数据。若无本地数据则返回 None。"""
    if not PLAYER_DATA_DIR.exists():
        return None

    target_prefix = f"{game_id.lower()}_"
    candidates: list[Tuple[int, Path]] = []

    for file in PLAYER_DATA_DIR.glob("*.json"):
        if not file.is_file():
            continue
        if file.name.lower().startswith(target_prefix):
            parts = file.stem.split("_")
            ts = int(parts[-1]) if len(parts) >= 3 and parts[-1].isdigit() else 0
            candidates.append((ts, file))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    latest_file = candidates[0][1]

    try:
        data = json.loads(latest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        logger.warning(f"[GTAOnline · 数据存储] 读取本地快照 {latest_file.name} 失败: {e}")
        return None
    return latest_file, data
