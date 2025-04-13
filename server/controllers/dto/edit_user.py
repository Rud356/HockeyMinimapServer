from typing import Optional

from pydantic import BaseModel, Field


class EditUser(BaseModel):
    """
    Тело запроса на изменение пользователя.
    """
    username: Optional[str] = Field(min_length=1, max_length=255)
    display_name: Optional[str] = Field(min_length=1, max_length=255)
    password: Optional[str] = Field(min_length=8, max_length=256)
