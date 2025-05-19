from pydantic import BaseModel

from server.algorithms.enums import Team


class ChangeAliasTeamRequest(BaseModel):
    new_team: Team
