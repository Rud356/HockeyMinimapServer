from typing import Optional, Protocol, runtime_checkable

from server.data_storage.dto import UserPermissionsDTO
from server.data_storage.dto.user_dto import UserDTO
from server.data_storage.dto.user_permissions_data import UserPermissionsData
from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class UserRepo(Protocol):
    """
    Описывает действия, допустимые для произведения над данными пользователей.
    """

    transaction: TransactionManager

    async def create_user(
        self,
        username: str,
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
        :raises IntegrityError: Данные не прошли проверку на валидность для вставки.
        """

    async def get_user(self, user_id: int) -> UserDTO:
        """
        Получает информацию о пользователе по идентификатору.

        :param user_id: Идентификатор пользователя.
        :return: Данные о пользователе.
        :raises NotFoundError: Пользователь не найден.
        :raises ValueError: Неверные входные данные.
        """

    async def get_users(self, limit: int = 100, offset: int = 0) -> list[UserDTO]:
        """
        Получает список пользователей.

        :param limit: Количество пользователей для получения.
        :param offset: Отступ от начала множества пользователей.
        :return: Пользователи.
        """

    async def delete_user(self, user_id: int) -> bool:
        """
        Удаляет пользователя из базы данных без фиксации в БД.

        :param user_id: Идентификатор пользователя для удаления.
        :return: Был ли пользователь успешно удален.
        :raises NotFoundError: Пользователь не найден.
        """

    async def change_user_permissions(
        self, user_id: int, new_permissions: UserPermissionsData
    ) -> UserPermissionsDTO:
        """
        Изменяет права пользователя на новые права.

        :param user_id: Идентификатор пользователя для изменения.
        :param new_permissions: Новые права пользователя.
        :return: Обновленное состояние прав пользователя.
        :raises NotFoundError: Пользователь не найден.
        """

    async def edit_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        display_name: Optional[str] = None,
        password: Optional[str] = None
    ) -> UserDTO:
        """
        Изменяет данные пользователя.

        :param user_id: Идентификатор пользователя.
        :param username: Новое имя пользователя.
        :param display_name: Новое отображаемое имя.
        :param password: Новый пароль.
        :return: Новое представление пользователя.
        :raises NotFoundError: Пользователь не найден.
        :raises ValueError: Неверные входные данные.
        """

    async def authenticate_user(self, username: str, password: str) -> UserDTO:
        """
        Аутентифицирует пользователя по предоставленному имени пользователя и паролю.

        :param username: Имя пользователя.
        :param password: Пароль.
        :return: Представление пользователя.
        :raise ValueError: Если предоставленные данные не являются валидными.
        """
