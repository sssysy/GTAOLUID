from typing import Any, Dict

PLATFORM_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "0": {
        "name": "GTA 增强版",
        "api": "pcalt",
    },
    "1": {
        "name": "GTA 传承版",
        "api": "pc",
    },
    "2": {
        "name": "PS 版",
        "api": "ps",
    },
    "3": {
        "name": "Xbox 版",
        "api": "xbox",
    },
}

DEFAULT_PLATFORM_CODE = "0"


def normalize_platform(raw: str | None) -> str:
    """仅按代码 0、1、2、3 严格匹配平台，未传时默认 0，严禁添加别名兼容。"""
    if not raw or not raw.strip():
        return DEFAULT_PLATFORM_CODE

    cleaned = raw.strip()
    if cleaned in PLATFORM_DEFINITIONS:
        return cleaned

    return DEFAULT_PLATFORM_CODE


def get_platform_name(code: str) -> str:
    """获取平台展示名称。"""
    return PLATFORM_DEFINITIONS.get(code, PLATFORM_DEFINITIONS[DEFAULT_PLATFORM_CODE])["name"]


def get_platform_api(code: str) -> str:
    """获取 API 平台标识。"""
    return PLATFORM_DEFINITIONS.get(code, PLATFORM_DEFINITIONS[DEFAULT_PLATFORM_CODE])["api"]


_API_TO_CODE: Dict[str, str] = {info["api"]: code for code, info in PLATFORM_DEFINITIONS.items()}


def get_platform_name_by_api(api_code: str) -> str:
    """按接口平台标识取展示名称；未收录的标识原样返回。"""
    raw = (api_code or "").strip()
    code = _API_TO_CODE.get(raw.lower())
    if code is None:
        return raw
    return PLATFORM_DEFINITIONS[code]["name"]


def format_platform_guide() -> str:
    """生成平台代码引导列表提示文本。"""
    lines = [f"{code}：{info['name']}" for code, info in PLATFORM_DEFINITIONS.items()]
    return "\n".join(lines)
