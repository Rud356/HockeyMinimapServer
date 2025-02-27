from __future__ import annotations

from typing import NamedTuple

from server.algorithms.data_types.relative_point import RelativePoint


class RelativeBoundingBox(NamedTuple):
    """
    Класс для представления
    """
    min_point: RelativePoint
    max_point: RelativePoint
