from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from server.algorithms.data_types.bounding_box import BoundingBox


class Point(NamedTuple):
    """
    Класс точки в двухмерном пространстве.
    """
    x: float
    y: float

    def clip_point_to_bounding_box(self, bounding_box: BoundingBox) -> Point:
        """
        Помещает точку в пространство ограничивающего прямоугольника.

        :param bounding_box: Ограничивающий прямоугольник.
        :return: Новая точка в границах прямоугольника.
        """
        return Point(
            float(np.clip(self.x, bounding_box.min_point.x, bounding_box.max_point.x)),
            float(np.clip(self.y, bounding_box.min_point.y, bounding_box.max_point.y))
        )

    def visualize_point_on_image(
        self,
        image: np.ndarray,
        color: tuple[int, int, int] = (128, 38, 128)
    ) -> np.ndarray:
        return cv2.circle(
            image,
            (int(self.x),
             int(self.y)),
            radius=5,
            color=color,
            thickness=-1
        )
