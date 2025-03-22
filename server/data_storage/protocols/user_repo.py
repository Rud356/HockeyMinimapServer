from typing import NamedTuple, Protocol, runtime_checkable

from server.data_storage.dto.user_dto import UserDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


class UserPermissionsData(NamedTuple):
    can_administrate_users: bool
    can_create_projects: bool


@runtime_checkable
class UserRepo(Protocol):
    """
    Описывает действия, допустимые для произведения над данными пользователей.
    """

    transaction: TransactionManager

    async def create_user(
        self, username: str,
        display_name: str,
        password: str,
        user_permissions: UserPermissionsData
    ) -> UserDTO:
        ...

    async def get_user(self, user_id: int) -> UserDTO:
        ...

    async def get_users(self, limit: int = 100, offset: int = 0) -> list[UserDTO]:
        ...

    async def delete_user(self, user_id: int) -> bool:
        ...

    async def change_user_permissions(self, user_id: int, new_permissions: UserPermissionsData) -> UserPermissionsData:
        ...

    async def authenticate_user(self, username: str, password: str) -> UserDTO:
        ...
