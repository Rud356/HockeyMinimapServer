from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

import cv2
import numpy

if TYPE_CHECKING:
    from server.algorithms.data_types.point import Point


class BoundingBox(NamedTuple):
    """
    Представляет ограничивающий прямоугольник в двухмерном пространстве.
    """
    min_point: Point
    max_point: Point

    def visualize_bounding_box(self, image: numpy.ndarray) -> numpy.ndarray:
        """
        Визуализирует прямоугольник на изображении.

        :param image: Исходное изображение.
        :return: Изображение с прямоугольником.
        """
        return cv2.rectangle(image, self.min_point, self.max_point, (0, 255, 0), 2)

    @classmethod
    def calculate_combined_bbox(cls, *bounding_boxes) -> BoundingBox:
        x_min = min(bbox[0] for bbox in bounding_boxes)
        y_min = min(bbox[1] for bbox in bounding_boxes)
        x_max = max(bbox[2] for bbox in bounding_boxes)
        y_max = max(bbox[3] for bbox in bounding_boxes)

        return BoundingBox(
            Point(x_min, y_min), Point(x_max, y_max)
        )
