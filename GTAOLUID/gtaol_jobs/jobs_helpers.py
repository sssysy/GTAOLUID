"""差事筛选解析、展示字段翻译与图片数据 URI 转换。"""

import base64
from pathlib import Path
from dataclasses import field, dataclass

from .jobs_map import (
    SORT_MAP,
    SOURCE_MAP,
    SUBTYPE_MAP,
    DEFAULT_SORT,
    MODE_NAME_MAP,
    DATE_RANGE_MAP,
    MISSION_TYPE_MAP,
    VEHICLE_CLASS_MAP,
    DEFAULT_DATE_RANGE,
)
from ..utils.downloader import download

# 标签回显与冲突提示按该顺序分组，保证同类条件的输出位置稳定
_CATEGORY_ORDER = ("date", "missiontype", "subtype", "source", "sort")

_CATEGORY_LABELS = {
    "date": "时间范围",
    "missiontype": "差事类型",
    "subtype": "差事类型",
    "source": "差事来源",
    "sort": "排序",
}

_WORD_INDEX = sorted(
    [
        *[(word, "date") for word in DATE_RANGE_MAP],
        *[(word, "source") for word in SOURCE_MAP],
        *[(word, "sort") for word in SORT_MAP],
        *[(word, "missiontype") for word in MISSION_TYPE_MAP],
        *[(word, "subtype") for word in SUBTYPE_MAP],
    ],
    key=lambda item: len(item[0]),
    reverse=True,
)

_IMAGE_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF8", "image/gif"),
)


@dataclass
class JobsFilter:
    """差事推荐的筛选条件解析结果。"""

    date_range: str = DEFAULT_DATE_RANGE
    mission_type: str | None = None
    subtype: str | None = None
    source: str | None = None
    sort: str = DEFAULT_SORT
    matched_labels: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


def _unique(words: list[str]) -> list[str]:
    """按出现顺序去重。"""
    return list(dict.fromkeys(words))


def _scan_words(text: str) -> list[tuple[str, str]]:
    """最长匹配优先扫描全文，返回 [类别, 词] 命中序列，未命中残片忽略。"""
    hits: list[tuple[str, str]] = []
    index = 0
    while index < len(text):
        for word, category in _WORD_INDEX:
            if text.startswith(word, index):
                hits.append((category, word))
                index += len(word)
                break
        else:
            index += 1
    return hits


def parse_jobs_filter(text: str) -> JobsFilter:
    """解析输入中的筛选词；同类命中多个不同词时只回冲突提示，不发请求。"""
    groups: dict[str, list[str]] = {}
    for category, word in _scan_words(text or ""):
        groups.setdefault(category, []).append(word)

    conflicts = []
    for category in _CATEGORY_ORDER:
        words = _unique(groups.get(category, []))
        if len(words) > 1:
            label = _CATEGORY_LABELS[category]
            conflicts.append(f"{label}冲突：{' 和 '.join(words)}")

    # subtype 必须与父 missiontype 同时成立，主类型与子类型跨父即冲突
    types = _unique(groups.get("missiontype", []))
    subs = _unique(groups.get("subtype", []))
    if len(types) == 1 and len(subs) == 1 and MISSION_TYPE_MAP[types[0]] != SUBTYPE_MAP[subs[0]][0]:
        conflicts.append(f"差事类型冲突：{types[0]} 和 {subs[0]}")

    if conflicts:
        return JobsFilter(conflicts=conflicts)

    result = JobsFilter()
    if types:
        result.mission_type = MISSION_TYPE_MAP[types[0]]
    if subs:
        result.mission_type, result.subtype = SUBTYPE_MAP[subs[0]]
    if groups.get("date"):
        result.date_range = DATE_RANGE_MAP[groups["date"][0]]
    if groups.get("source"):
        result.source = SOURCE_MAP[groups["source"][0]]
    if groups.get("sort"):
        result.sort = SORT_MAP[groups["sort"][0]]

    for category in _CATEGORY_ORDER:
        words = _unique(groups.get(category, []))
        if words:
            result.matched_labels.append(words[0])

    return result


def get_mode_name(raw_type: str | None) -> str | None:
    """接口 type 去掉 P2P 后缀后查官方中文；未收录时原样返回。"""
    raw = (raw_type or "").strip()
    if not raw:
        return None
    key = raw.upper()
    if key.endswith("P2P"):
        key = key[:-3]
    return MODE_NAME_MAP.get(key, raw)


def get_vehicle_class_name(raw: str | None) -> str | None:
    """接口 vehcl 取值查官方中文；未收录时原样返回。"""
    value = (raw or "").strip()
    if not value:
        return None
    return VEHICLE_CLASS_MAP.get(value, value)


def _guess_mime(data: bytes) -> str:
    """按文件头判定图片类型；无法识别时回落 image/jpeg。"""
    for magic, mime in _IMAGE_MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def image_path_to_data_uri(path: Path | None) -> str:
    """本地图片文件转 data URI；文件缺失或为空返回空串。"""
    if path is None or not path.is_file() or path.stat().st_size <= 0:
        return ""
    data = path.read_bytes()
    return f"data:{_guess_mime(data)};base64,{base64.b64encode(data).decode('ascii')}"


async def load_job_image_data_uri(url: str | None) -> str:
    """经统一下载入口取回单张差事图片并转 data URI；失败返回空串。"""
    target = (url or "").strip()
    if not target:
        return ""
    return image_path_to_data_uri(await download(target))
