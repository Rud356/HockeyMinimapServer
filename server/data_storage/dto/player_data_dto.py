from typing import Optional

from pydantic import BaseModel

from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team
from server.data_storage.dto.box_dto import BoxDTO
from server.data_storage.dto.point_dto import PointDTO


class PlayerDataDTO(BaseModel):
    tracking_id: int
    player_id: Optional[int]
    player_name: Optional[str]
    team_id: Optional[Team]
    class_id: PlayerClasses
    player_on_camera: BoxDTO
    player_on_minimap: PointDTO
