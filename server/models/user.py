from server.data_storage.protocols.repository import Repository
from server.models.user_permissions import UserPermissions


class User:
    user_id: int
    username: str
    display_name: str
    permissions: UserPermissions
    data_repository: Repository

    def __init__(
        self,
        user_id: int,
        username: str,
        display_name: str,
        permissions: UserPermissions,
        data_repository: Repository
    ):
        self.user_id = user_id
        self.username = username
        self.display_name = display_name
        self.permissions = permissions
        self.data_repository = data_repository

    @classmethod
    async def create_user(
        cls, username: str, display_name: str,
        password: str, permissions: UserPermissions
    ) -> "User":
        ...

    @classmethod
    async def get_user(cls, user_id: int) -> "User":
        ...

    @classmethod
    async def authenticate(cls, username: str, password: str) -> "User":
        ...
