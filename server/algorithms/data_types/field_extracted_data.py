from typing import NamedTuple

from server.algorithms.data_types import Mask, Point
from server.utils.config.key_point import KeyPoint


class FieldExtractedData(NamedTuple):
    key_points: dict[KeyPoint, Point]
    map_mask: Mask
