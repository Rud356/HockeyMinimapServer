from typing import Optional

from pydantic import BaseModel, Field


class EditProject(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    team_home_name: Optional[str] = Field(default=None, min_length=1, max_length=30)
    team_away_name: Optional[str] = Field(default=None, min_length=1, max_length=30)
