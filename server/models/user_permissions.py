from server.data_storage.protocols.repository import Repository


class UserPermissions:
    create_projects: bool
    administrate_users: bool

    def __init__(self, create_projects: bool, administrate_users: bool):
        self.create_projects = create_projects
        self.administrate_users = administrate_users

    @classmethod
    async def load_permissions(
        cls, user_id: int, data_repository: Repository
    ) -> "UserPermissions":
        ...
