import datetime

from pydantic import BaseModel


class ProjectDTO(BaseModel):
    project_id: int
    for_video_id: int
    name: str
    created_at: datetime.datetime
    team_home_name: str
    team_away_name: str
