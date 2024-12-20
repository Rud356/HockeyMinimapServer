from server.data_storage.repository import Repository


class UserPermissions:
    create_projects: bool
    administrate_users: bool

    @classmethod
    async def load_permissions(cls, user_id: int, data_repository: Repository) -> "UserPermissions":
        ...
