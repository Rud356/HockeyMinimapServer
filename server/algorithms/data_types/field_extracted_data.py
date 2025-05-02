from typing import NamedTuple

from server.algorithms.data_types import BoundingBox, Mask, RelativePoint
from server.utils.config.key_point import KeyPoint


class FieldExtractedData(NamedTuple):
    key_points: dict[KeyPoint, RelativePoint]
    map_mask: Mask
    field_bbox: BoundingBox
