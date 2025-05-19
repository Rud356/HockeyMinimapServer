from pydantic import BaseModel


class PlayerAliasCreatedResponse(BaseModel):
    player_alias_id: int
