from typing import Optional
from dataclasses import dataclass

from server.algorithms.data_types.relative_point import RelativePoint
from server.algorithms.data_types.relative_bounding_box import RelativeBoundingBox
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.enums.team import Team


@dataclass(frozen=True, slots=True)
class PlayerData:
    """
    Описывает данные об игроке для отрисовки.
    """

    tracking_id: int
    user_id: Optional[str]
    position: RelativePoint
    bounding_box_on_camera: RelativeBoundingBox
    class_id: PlayerClasses
    team_id: Optional[Team] = None
