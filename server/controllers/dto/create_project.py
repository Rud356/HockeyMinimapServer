from typing import Optional

from pydantic import BaseModel, Field


class CreateProject(BaseModel):
    for_video_id: int
    name: str = Field(min_length=1, max_length=50)
    team_home_name: Optional[str] = Field(default=None, min_length=1, max_length=30)
    team_away_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
