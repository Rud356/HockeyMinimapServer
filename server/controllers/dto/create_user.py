from pydantic import BaseModel, Field

from server.data_storage.dto import UserPermissionsDTO


class CreateUser(BaseModel):
    """
    Тело запроса на создание пользователя.
    """
    user_permissions: UserPermissionsDTO
    username: str = Field(min_length=1, max_length=255)
    display_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=256)
