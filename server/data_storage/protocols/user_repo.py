from typing import NamedTuple, Optional, Protocol, runtime_checkable

from server.data_storage.dto.user_dto import UserDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


class UserPermissionsData(NamedTuple):
    """
    Перечисление прав пользователя.
    """
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
        """
        Создает нового пользователя системы в базе данных.

        :param username: Имя пользователя для входа.
        :param display_name: Отображаемое имя пользователя.
        :param password: Пароль пользователя.
        :param user_permissions: Права пользователя.
        :return: Данные о новом пользователе.
        """
        ...

    async def get_user(self, user_id: int) -> UserDTO:
        """
        Получает информацию о пользователе по идентификатору.

        :param user_id: Идентификатор пользователя.
        :return: Данные о пользователе.
        """
        ...

    async def get_users(self, limit: int = 100, offset: int = 0) -> list[UserDTO]:
        """
        Получает список пользователей.

        :param limit: Количество пользователей для получения.
        :param offset: Отступ от начала множества пользователей.
        :return: Пользователи.
        """
        ...

    async def delete_user(self, user_id: int) -> bool:
        """
        Удаляет пользователя из базы данных.

        :param user_id: Идентификатор пользователя для удаления.
        :return: Был ли пользователь успешно удален.
        """
        ...

    async def change_user_permissions(self, user_id: int, new_permissions: UserPermissionsData) -> UserPermissionsData:
        """
        Изменяет права пользователя на новые права.

        :param user_id: Идентификатор пользователя для изменения.
        :param new_permissions:
        :return:
        """
        ...

    async def edit_user(
        self, user_id: int,
        username: Optional[str],
        display_name: Optional[str],
        password: Optional[str]
    ) -> UserDTO:
        """
        Изменяет данные пользователя.

        :param user_id: Идентификатор пользователя.
        :param username: Новое имя пользователя.
        :param display_name: Новое отображаемое имя.
        :param password: Новый пароль.
        :return: Новое представление пользователя.
        """
        ...

    async def authenticate_user(self, username: str, password: str) -> UserDTO:
        """
        Аутентифицирует пользователя по предоставленному имени пользователя и паролю.

        :param username: Имя пользователя.
        :param password: Пароль.
        :return: Представление пользователя.
        """
        ...
