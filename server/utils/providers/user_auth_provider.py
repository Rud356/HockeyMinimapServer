from dishka import Provider, Scope, provide

from server.controllers.services.user_authorization_service import UserAuthorizationService


class UserAuthorizationProvider(Provider):
    def __init__(self, user_auth_service: UserAuthorizationService):
        super().__init__()
        self.user_auth_service = user_auth_service

    @provide(scope=Scope.REQUEST)
    def get_user_auth_service(self) -> UserAuthorizationService:
        return self.user_auth_service
