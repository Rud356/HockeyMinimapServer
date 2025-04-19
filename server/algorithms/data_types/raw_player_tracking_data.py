from typing import NamedTuple

from server.algorithms.data_types.bounding_box import BoundingBox
from server.algorithms.enums.player_classes_enum import PlayerClasses


class RawPlayerTrackingData(NamedTuple):
    """
    Информация из алгоритма отслеживания игроков.
    """

    tracking_id: int
    bounding_box: BoundingBox
    player_class: PlayerClasses
    score: float
