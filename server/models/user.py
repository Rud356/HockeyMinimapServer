from server.data_storage.repository import Repository
from server.models.user_permissions import UserPermissions


class User:
    user_id: int
    username: str
    display_name: str
    permissions: UserPermissions
    data_repository: Repository

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
