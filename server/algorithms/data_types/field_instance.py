from dataclasses import dataclass

from server.algorithms.data_types.bounding_box import BoundingBox
from server.algorithms.data_types.mask import Mask
from server.algorithms.data_types.point import Point
from server.algorithms.enums.field_classes_enum import FieldClasses


@dataclass(repr=True)
class FieldInstance:
    """
    Описывает одно значение из Detectron2 связанное с полем.
    """
    bbox: BoundingBox
    polygon: Mask
    center_point: Point
    class_id: FieldClasses
