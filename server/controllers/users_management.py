from typing import Annotated

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, HTTPException
from fastapi.params import Query

from server.controllers.dto import CreateUser, EditUser, UserIsDeleted
from server.controllers.endpoints_base import APIEndpoint
from server.controllers.exceptions import UnauthorizedResourceAccess
from server.data_storage.dto import UserDTO, UserPermissionsDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import Repository
from server.views.user_view import UserView


class UserManagementEndpoint(APIEndpoint):
    """
    Описывает эндпоинт апи для взаимодействия с пользователями.
    """
    def __init__(self, router: APIRouter):
        super().__init__(router)
        self.router.add_api_route(
            "/users",
            self.list_users,
            description="Получает список пользователей",
            methods=["get"],
            responses={
                200: {"description": "Возвращает список пользователей"},
                401: {
                    "description":
                        "Нет валидного токена авторизации или нет прав на доступ к ресурса"
                }
            },
            tags=["users", "admin"]
        )
        self.router.add_api_route(
            "/users/me",
            self.get_current_user_information,
            description="Получает информацию о текущем пользователе",
            methods=["get"],
            responses={
                200: {"description": "Возвращает информацию о пользователе"},
                401: {"description": "Нет валидного токена авторизации"}
            },
            tags=["users"]
        )
        self.router.add_api_route(
            "/users/{user_id}",
            self.get_information_about_user,
            description="Получает информацию о пользователе с идентификатором",
            methods=["get"],
            responses={
                200: {"description": "Возвращает информацию о пользователе"},
                401: {"description": "Нет валидного токена авторизации"},
                404: {"description": "Нет такого пользователя"}
            },
            tags=["users", "admin"]
        )
        self.router.add_api_route(
            "/users/{user_id}",
            self.delete_user,
            description="Удаляет пользователя из базы данных",
            methods=["delete"],
            responses={
                200: {"description": "Пользователь успешно удален"},
                401: {"description": "Нет валидного токена авторизации"},
                404: {"description": "Нет такого пользователя"}
            },
            tags=["users", "admin"]
        )
        self.router.add_api_route(
            "/users/",
            self.create_user,
            description="Изменяет пользователя в базе данных",
            methods=["post"],
            responses={
                200: {"description": "Пользователь успешно изменен"},
                400: {"description": "Неправильные данные в теле запроса"},
                401: {"description": "Нет валидного токена авторизации"},
            },
            tags=["users", "admin"]
        )
        self.router.add_api_route(
            "/users/{user_id}",
            self.edit_user,
            description="Изменяет пользователя в базе данных",
            methods=["patch"],
            responses={
                200: {"description": "Пользователь успешно изменен"},
                400: {"description": "Неправильные данные в теле запроса"},
                401: {"description": "Нет валидного токена авторизации"},
                404: {"description": "Нет такого пользователя"}
            },
            tags=["users", "admin"]
        )
        self.router.add_api_route(
            "/users/{user_id}/permissions",
            self.change_permissions,
            description="Изменяет права пользователя",
            methods=["patch"],
            responses={
                200: {"description": "Пользователь успешно изменен"},
                400: {"description": "Неправильные данные в теле запроса"},
                401: {"description": "Нет валидного токена авторизации"},
                404: {"description": "Нет такого пользователя"}
            },
            tags=["users", "admin"]
        )

    async def list_users(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        limit: Annotated[int, Query(ge=1, le=250)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0
    ) -> list[UserDTO]:
        """
        Выводит список пользователей.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param limit: Сколько записей получить.
        :param offset: Сколько записей отступить от начала.
        :return: Список пользователей.
        """
        if not current_user.user_permissions.can_administrate_users:
            raise UnauthorizedResourceAccess(
                "User is required to have access to administrating rights"
            )

        return await UserView(repository).get_users(limit, offset)

    async def get_information_about_user(
        self,
        user_id: int,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO]
    ) -> UserDTO:
        """
        Получает информацию о пользователе.

        :param current_user: Пользователь системы.
        :param repository: Объект взаимодействия с БД.
        :param user_id: О каком пользователе получить информацию.
        :return: Информация о пользователе.
        """
        if not current_user.user_permissions.can_administrate_users:
            raise UnauthorizedResourceAccess(
                "User is required to have access to administrating rights"
            )

        if (user_info := await UserView(repository).get_user(user_id)) is not None:
            return user_info

        raise HTTPException(status_code=404, detail="User not found with provided ID")

    async def get_current_user_information(
        self,
        current_user: FromDishka[UserDTO]
    ) -> UserDTO:
        """
        Получает информацию о текущем пользователе.

        :param current_user: Пользователь системы.
        :return: Информация о пользователе.
        """
        return current_user

    async def delete_user(
        self,
        user_id: int,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO]
    ) -> UserIsDeleted:
        """
        Удаляет пользователя из БД.

        :param user_id: Идентификатор.
        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :return: Сообщения об удалении.
        """
        if not current_user.user_permissions.can_administrate_users:
            raise UnauthorizedResourceAccess(
                "User is required to have access to administrating rights"
            )

        if user_has_been_deleted := await UserView(repository).delete_user(user_id):
            return UserIsDeleted(user_id=user_id, deleted=user_has_been_deleted)

        raise HTTPException(status_code=404, detail="User not found with provided ID")

    async def create_user(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        user_data: CreateUser,
    ) -> UserDTO:
        """
        Создает нового пользователя в системе.

        :param repository: Объект для взаимодействия с БД.
        :param user_data: Данные нового пользователя.
        :param current_user: Пользователь системы.
        :return: Информация о пользователе.
        """
        if not current_user.user_permissions.can_administrate_users:
            raise UnauthorizedResourceAccess(
                "User is required to have access to administrating rights"
            )

        try:
            return await UserView(repository).create_user(
                user_data.username,
                user_data.display_name,
                user_data.password,
                user_data.user_permissions
            )

        except DataIntegrityError as err:
            raise HTTPException(
                400, "Invalid data in user creation body (duplicate possible)"
            ) from err

    async def edit_user(
        self,
        user_id: int,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        user_edit: EditUser
    ) -> UserDTO:
        """
        Изменяет пользователя.

        :param user_id: Какой пользователь изменяется.
        :param repository: Объект для взаимодействия с БД.
        :param user_edit: Изменения в объекте пользователя.
        :param current_user: Пользователь системы.
        :return: Обновленные данные.
        """
        if not current_user.user_permissions.can_administrate_users:
            raise UnauthorizedResourceAccess(
                "User is required to have access to administrating rights"
            )

        try:
            return await UserView(repository).edit_user(
                user_id, user_edit.username, user_edit.display_name, user_edit.password
            )

        except NotFoundError:
            raise HTTPException(404, detail="User was not found")

        except ValueError:
            raise HTTPException(400, detail="Invalid body")

    async def change_permissions(
        self,
        user_id: int,
        new_permissions: UserPermissionsDTO,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
    ) -> UserPermissionsDTO:
        """
        Обновляет права пользователя.

        :param user_id: Идентификатор.
        :param new_permissions:
        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :return: Обновленные права.
        """
        if not current_user.user_permissions.can_administrate_users:
            raise UnauthorizedResourceAccess(
                "User is required to have access to administrating rights"
            )

        try:
            return await UserView(repository).change_user_permissions(
                user_id, new_permissions
            )

        except NotFoundError as err:
            raise HTTPException(404, detail="User was not found") from err

        except ValueError as err:
            raise HTTPException(400, detail="Invalid body") from err
