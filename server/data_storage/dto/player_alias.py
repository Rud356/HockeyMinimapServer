from pydantic import BaseModel

from server.algorithms.enums import Team


class PlayerAlias(BaseModel):
    alias_id: int
    player_name: str | None
    player_team: Team | None
