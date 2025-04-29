from typing import Optional

from server.data_storage.dto import UserDTO, UserPermissionsDTO, UserPermissionsData
from server.data_storage.exceptions import NotFoundError
from server.data_storage.protocols import Repository


class UserView:
    """
    Предоставляет интерфейс получения данных о пользователях и управления ими.
    """
    def __init__(self, repository: Repository):
        self.repository = repository

    async def get_users(self, limit: int = 100, offset: int = 0) -> list[UserDTO]:
        """
        Получает пользователей системы, отсортированными по возрастанию идентификаторов.

        :param limit: Сколько пользователей получить.
        :param offset: Отступ от начала.
        :return: Список пользователей.
        """
        async with self.repository.transaction:
            return await self.repository.user_repo.get_users(limit, offset)

    async def get_user(self, user_id: int) -> UserDTO | None:
        """
        Получает пользователя под идентификатором.

        :param user_id: Идентификатор пользователя.
        :return: Информация о пользователе или ничего.
        """
        try:
            async with self.repository.transaction:
                return await self.repository.user_repo.get_user(user_id)

        except (ValueError, NotFoundError):
            return None

    async def delete_user(self, user_id: int) -> bool:
        """
        Удаляет пользователя из базы данных.

        :param user_id: Идентификатор пользователя.
        :return: Был ли удален пользователь.
        """
        async with self.repository.transaction:
            return await self.repository.user_repo.delete_user(user_id)

    async def create_user(
        self,
        username: str,
        display_name: str,
        password: str,
        user_permissions: UserPermissionsDTO
    ) -> UserDTO:
        """
        Создает нового пользователя системы в базе данных.

        :param username: Имя пользователя для входа.
        :param display_name: Отображаемое имя пользователя.
        :param password: Пароль пользователя.
        :param user_permissions: Права пользователя.
        :return: Данные о новом пользователе.
        :raises DataIntegrityError: Данные не прошли проверку на валидность для вставки.
        """
        async with self.repository.transaction as tr:
            new_user: UserDTO = await self.repository.user_repo.create_user(
                username=username,
                display_name=display_name,
                password=password,
                user_permissions=UserPermissionsData(
                    can_administrate_users=user_permissions.can_administrate_users,
                    can_create_projects=user_permissions.can_create_projects
                )
            )
            await tr.commit()
        return new_user

    async def authenticate_user(self, username: str, password: str) -> UserDTO:
        """
        Аутентифицирует пользователя по предоставленному имени пользователя и паролю.

        :param username: Имя пользователя.
        :param password: Пароль.
        :return: Представление пользователя.
        :raise ValueError: Если предоставленные данные не являются валидными.
        """
        async with self.repository.transaction:
            return await self.repository.user_repo.authenticate_user(
                username, password
            )

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
        async with self.repository.transaction as tr:
            edited_user: UserDTO = await self.repository.user_repo.edit_user(
                user_id,
                username,
                display_name,
                password
            )
            await tr.commit()
        return edited_user

    async def change_user_permissions(
        self, user_id: int, new_permissions: UserPermissionsDTO
    ) -> UserPermissionsDTO:
        """
        Изменяет права пользователя на новые права.

        :param user_id: Идентификатор пользователя для изменения.
        :param new_permissions: Новые права пользователя.
        :return: Обновленное состояние прав пользователя.
        :raises NotFoundError: Пользователь не найден.
        :raises ValueError: Неверные входные данные.
        """
        async with self.repository.transaction as tr:
            new_permissions = await self.repository.user_repo.change_user_permissions(
                user_id=user_id,
                new_permissions=UserPermissionsData(
                    can_administrate_users=new_permissions.can_administrate_users,
                    can_create_projects=new_permissions.can_create_projects
                )
            )
            await tr.commit()

        return new_permissions
