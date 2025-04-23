from typing import Any

import jwt
from fastapi import Response
from pydantic import ValidationError

from server.controllers.exceptions import BadTokenPayload, UnauthorizedResourceAccess
from server.data_storage.dto import UserDTO, UserPermissionsDTO
from server.data_storage.protocols import Repository


class UserAuthorizationService:
    def __init__(self, key: str, local_mode: bool = False):
        self.key: str = key
        self.local_mode: bool = local_mode

    def encode_user_auth_token(self, user: UserDTO) -> str:
        """
        Создает токен авторизации пользователя.

        :param user: Объект с данными пользователя.
        :return: Токен доступа.
        """
        return jwt.encode(user.model_dump(), self.key, algorithm="HS256")

    def decode_user_auth_token(self, token: str | None) -> UserDTO:
        """
        Декодирует полученный токен в данные.

        :param token: Полученный токен из пользовательских данных.
        :return: Объект пользователя.
        :raises BadTokenPayload: Если токен отсутствует или неверного формата.
        """
        if token is None:
            raise BadTokenPayload()

        try:
            payload: dict[str, Any] = jwt.decode(token, self.key, algorithms=["HS256"])

            return UserDTO.model_validate(payload)

        except ValidationError as err:
            raise BadTokenPayload() from err

    async def authenticate_decoded_token(self, data: UserDTO, repository: Repository) -> bool:
        """
        Проверяет подлинность пользователя.

        :param data: Данные о пользователе из базы данных.
        :param repository: Репозиторий с данными.
        :return: Подтверждена ли авторизация.
        """
        if self.local_mode and data.username == "Admin":
            return True

        async with repository.transaction:
            repository_data: UserDTO = await repository.user_repo.get_user(user_id=data.user_id)

        return repository_data == data

    async def authenticate_by_token(self, token: str | None, repository: Repository) -> UserDTO:
        """
        Производит аутентификацию пользователя.

        :param token: Токен пользователя.
        :param repository:
        :return:
        """
        decoded_token: UserDTO = self.decode_user_auth_token(token)

        if await self.authenticate_decoded_token(decoded_token, repository):
            return decoded_token

        raise UnauthorizedResourceAccess()

    @staticmethod
    def local_account_data() -> UserDTO:
        return UserDTO(
            user_id=0,
            username="Admin",
            display_name="Local admin",
            user_permissions=UserPermissionsDTO(
                can_administrate_users=True,
                can_create_projects=True
            )
        )

    @staticmethod
    async def invalidate_user_token_cookie() -> Response:
        """
        Удаляет куки файл пользователя.

        :return: HTTP ответ для удаления куки token с токеном пользователя.
        """

        response = Response()
        response.delete_cookie("user_token")
        return response
