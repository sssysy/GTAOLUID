from gsuid_core.webconsole.mount_app import PageSchema, GsAdminModel, site

from .models import GTAUser


@site.register_admin
class GTAUserAdmin(GsAdminModel):
    model = GTAUser
    page_schema = PageSchema(
        label="GTAOL账户管理",
        icon="fa fa-users",
    )
