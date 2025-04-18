from typing import Optional

from pydantic import BaseModel

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team
from server.data_storage.dto.box_dto import BoxDTO


class SubsetDataInputDTO(BaseModel):
    tracking_id: int
    frame_id: int
    class_id: PlayerClasses
    team_id: Optional[Team]
    box: BoxDTO
