from gsuid_core.sv import Plugins

Plugins(
    name="GTAOLUID",
    force_prefix=["gta"],
    allow_empty_prefix=False,
)

from . import gtaol_bind as gtaol_bind, gtaol_info as gtaol_info, gtaol_refresh as gtaol_refresh  # noqa: E402
