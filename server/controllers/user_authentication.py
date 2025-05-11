import datetime

from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from server.controllers.dto.user_auth import UserAuth
from server.controllers.endpoints_base import APIEndpoint
from server.controllers.services.user_authorization_service import UserAuthorizationService
from server.data_storage.dto import UserDTO
from server.data_storage.protocols import Repository
from server.views.user_view import UserView


class UserAuthenticationEndpoint(APIEndpoint):
    """
    Описывает эндпоинт апи управления авторизацией пользователя.
    """
    def __init__(self, router: APIRouter):
        super().__init__(router)
        self.router.add_api_route(
            "/auth/login",
            self.authenticate_user,
            description="Авторизует пользователя в системе",
            methods=["POST"],
            response_model=UserDTO,
            responses={
                200: {"description": "Пользователь успешно авторизован"},
                404: {"description": "Пользователь не найден или неверные данные для входа"}
            },
            tags=["users", "security"]
        )
        self.router.add_api_route(
            "/auth/logout",
            self.logout,
            description="Удаляет токен авторизации пользователя в системе",
            methods=["POST"],
            responses={
                200: {"description": "Пользователь успешно авторизован"},
                404: {"description": "Пользователь не найден или неверные данные для входа"}
            },
            tags=["users", "security"]
        )

    async def authenticate_user(
        self,
        user_auth_data: UserAuth,
        repository: FromDishka[Repository],
        user_auth_service: FromDishka[UserAuthorizationService]
    ) -> JSONResponse:
        """
        Аутентифицирует пользователя в системе.

        :param user_auth_data: Информация для проведения аутентификации.
        :param repository: Объект взаимодействия с БД.
        :param user_auth_service: Сервис авторизации пользователя.
        :return: Данные о пользователе.
        """
        try:
            if user_auth_service.local_mode and user_auth_data.username == "Admin":
                user: UserDTO = user_auth_service.local_account_data()

            else:
                user = await UserView(repository).authenticate_user(
                    user_auth_data.username, user_auth_data.password
                )

            response = JSONResponse(content=jsonable_encoder(user))

            # 7 days cookie lifetime
            cookie_lifetime: datetime.datetime = datetime.datetime.now(
                tz=datetime.UTC
            ) + datetime.timedelta(days=7)
            response.set_cookie(
                key="user_token",
                value=user_auth_service.encode_user_auth_token(user),
                httponly=False,
                expires=cookie_lifetime,
                secure=True,
                samesite="none",
                path="/"
            )

            return response

        except ValueError as err:
            raise HTTPException(404, detail="Invalid credentials or user doesn't exists") from err

    async def logout(self) -> Response:
        """
        Удаляет куки пользователя для выхода из аккаунта.

        :return: Новый ответ.
        """
        response: Response = Response()
        response.delete_cookie("user_token")

        return response
