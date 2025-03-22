from pydantic import BaseModel


class UserPermissionsDTO(BaseModel):
    can_administrate_users: bool
    can_create_projects: bool
