from dishka import Provider, Scope, from_context, provide
from fastapi import Request

from server.controllers.services.user_authorization_service import UserAuthorizationService
from server.data_storage.dto import UserDTO
from server.data_storage.protocols import Repository


class UserAuthorizationProvider(Provider):
    request = from_context(provides=Request, scope=Scope.REQUEST)

    def __init__(self, repository: Repository, user_auth_service: UserAuthorizationService):
        super().__init__()
        self.user_auth_service = user_auth_service
        self.repository = repository

    @provide(scope=Scope.REQUEST)
    def get_user_auth_service(self) -> UserAuthorizationService:
        return self.user_auth_service

    @provide(scope=Scope.REQUEST)
    async def authenticated_user(
        self,
        request: Request,
        repository: Repository
    ) -> UserDTO:
        return await self.user_auth_service.authenticate_by_token(
            request.cookies.get("user_token"), self.repository
        )
