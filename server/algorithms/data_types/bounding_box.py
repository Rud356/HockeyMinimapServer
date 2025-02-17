from __future__ import annotations

from typing import NamedTuple

import cv2
import numpy

from server.algorithms.data_types.point import Point


class BoundingBox(NamedTuple):
    """
    Представляет ограничивающий прямоугольник в двухмерном пространстве.
    """
    min_point: Point
    max_point: Point

    def visualize_bounding_box(
        self,
        image: numpy.ndarray,
        color: tuple[int, int, int] = (0, 255, 0)
    ) -> numpy.ndarray:
        """
        Визуализирует прямоугольник на изображении.

        :param color: Цвет прямоугольника.
        :param image: Исходное изображение.
        :return: Изображение с прямоугольником.
        """
        return cv2.rectangle(
            image,
            tuple(map(int, self.min_point)),
            tuple(map(int, self.max_point)),
            color,
            2
        )

    @classmethod
    def calculate_combined_bbox(cls, *bounding_boxes) -> BoundingBox:
        x_min = min(bbox[0] for bbox in bounding_boxes)
        y_min = min(bbox[1] for bbox in bounding_boxes)
        x_max = max(bbox[2] for bbox in bounding_boxes)
        y_max = max(bbox[3] for bbox in bounding_boxes)

        return BoundingBox(
            Point(x_min, y_min), Point(x_max, y_max)
        )
