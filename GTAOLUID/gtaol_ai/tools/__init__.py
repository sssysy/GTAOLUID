"""集中注册 GTAOL AI 工具。"""

# 导入业务模块以触发 @ai_tools 注册。
from . import bind, info, jobs  # noqa: F401
