from pydantic import BaseModel

from server.data_storage.dto.user_permissions_dto import UserPermissionsDTO


class UserDTO(BaseModel):
    """
    Описывает данные пользователя.
    """
    user_id: int
    username: int
    display_name: str
    user_permissions: UserPermissionsDTO
