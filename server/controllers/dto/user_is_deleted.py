from pydantic import BaseModel


class UserIsDeleted(BaseModel):
    user_id: int
    deleted: bool
