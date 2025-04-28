from typing import Literal

from pydantic import BaseModel


class UserAuth(BaseModel):
    username: str | Literal["Admin"]
    password: str
