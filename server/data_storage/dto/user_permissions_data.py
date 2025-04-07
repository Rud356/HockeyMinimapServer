from typing import NamedTuple


class UserPermissionsData(NamedTuple):
    """
    Перечисление прав пользователя.
    """
    can_administrate_users: bool
    can_create_projects: bool
