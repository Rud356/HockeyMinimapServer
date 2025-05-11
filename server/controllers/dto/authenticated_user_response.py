from server.data_storage.dto import UserDTO


class AuthenticatedUserResponse(UserDTO):
    token: str
