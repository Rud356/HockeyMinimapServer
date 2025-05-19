from pydantic import BaseModel, Field

from server.algorithms.enums import Team


class CreatePlayerAlias(BaseModel):
    player_team: Team
    alias_name: str = Field(min_length=1, max_length=50)
