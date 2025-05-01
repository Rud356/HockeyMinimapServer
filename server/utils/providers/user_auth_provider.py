from dishka import FromDishka, Provider, Scope, from_context, provide
from fastapi import Request

from server.controllers.services.user_authorization_service import UserAuthorizationService
from server.data_storage.dto import UserDTO
from server.data_storage.protocols import Repository
from server.utils.config import AppConfig


class UserAuthorizationProvider(Provider):
    request = from_context(provides=Request, scope=Scope.REQUEST)

    @provide(scope=Scope.REQUEST)
    def get_user_auth_service(self, config: FromDishka[AppConfig]) -> UserAuthorizationService:
        return UserAuthorizationService(
            key=config.server_jwt_key,
            local_mode=config.local_mode
        )

    @provide(scope=Scope.REQUEST)
    async def authenticated_user(
        self,
        request: Request,
        user_auth_service: UserAuthorizationService,
        repository: FromDishka[Repository]
    ) -> UserDTO:
        return await user_auth_service.authenticate_by_token(
            request.cookies.get("user_token"), repository
        )
