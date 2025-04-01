from __future__ import annotations

from typing import NamedTuple

import cv2
import numpy

from server.algorithms.data_types.point import Point
from server.algorithms.data_types.relative_bounding_box import RelativeBoundingBox


class BoundingBox(NamedTuple):
    """
    Представляет ограничивающий прямоугольник в двухмерном пространстве.
    """
    min_point: Point
    max_point: Point

    @property
    def center_point(self) -> Point:
        """
        Центральная точка ограничивающего прямоугольника.

        :return: Точка центра прямоугольника.
        """
        return Point(
            (self.min_point.x + self.max_point.x) / 2,
            (self.min_point.y + self.max_point.y) / 2
        )

    @property
    def bottom_point(self) -> Point:
        """
        Возвращает точку ограничивающего прямоугольника в центре нижней линии прямоугольника.

        :return: Точка центра нижней линии прямоугольника.
        """
        return Point(
            (self.min_point.x + self.max_point.x) / 2,
            self.max_point.y
        )

    def intersects_with(self, bbox: BoundingBox) -> bool:
        """
        Проверяет пересечение ограничивающего прямоугольника с другим прямоугольником.

        :return: Есть ли пересечение.
        """
        return not (
            self.min_point.x > bbox.max_point.x or
            self.max_point.x < bbox.min_point.x or
            self.min_point.y > bbox.max_point.y or
            self.max_point.y < bbox.min_point.y
        )

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

    def cut_out_image_part(self, image: numpy.ndarray) -> numpy.ndarray:
        """
        Cuts out the part of the image defined by the bounding box.

        :param image: Исходное изображение.
        :return: Вырезанная часть изображения внутри.
        """
        return image[
           int(self.min_point.y):int(self.max_point.y),
           int(self.min_point.x):int(self.max_point.x)
        ]

    def to_relative_coordinates(self, resolution: tuple[int, int]) -> RelativeBoundingBox:
        """
        Изменяет систему координат из абсолютной в относительную (значения от 0 до 1 в пространстве изображения).

        :param resolution: Размер изображения, в координатах которого получаем относительные координаты.
        :return: Ограничивающий прямоугольник в относительной системе координат.
        :raise ValueError: Если количество элементов в resolution не равно двум, или тип не int,
            или значения отрицательные, или ноль.
        """

        return RelativeBoundingBox(
            self.min_point.to_relative_coordinates(resolution),
            self.max_point.to_relative_coordinates(resolution)
        )

    @classmethod
    def calculate_combined_bbox(cls, *bounding_boxes: list[float]) -> BoundingBox:
        """
        Находит объединенный ограничивающий прямоугольник из нескольких прямоугольников.
        :param bounding_boxes: Списки из выходов от Detectron2, содержащие float
            значения в порядке x1, y1, x2, y2.
        :return: Новый ограничивающий прямоугольник.
        """
        x_min = min(bbox[0] for bbox in bounding_boxes)
        y_min = min(bbox[1] for bbox in bounding_boxes)
        x_max = max(bbox[2] for bbox in bounding_boxes)
        y_max = max(bbox[3] for bbox in bounding_boxes)

        return cls(
            Point(x_min, y_min), Point(x_max, y_max)
        )

    @classmethod
    def from_relative_bounding_box(cls, bbox: RelativeBoundingBox, resolution: tuple[int, int]):
        """
        Преобразует относительные координаты в абсолютные.

        :param bbox: Ограничивающий прямоугольник в относительных координатах.
        :param resolution: Размер изображения, в координатах которого получаем относительные координаты.
        :return: Ограничивающий прямоугольник в абсолютных координатах.
        :raise ValueError: Если количество элементов в resolution не равно двум, или тип не int,
            или значения отрицательные, или ноль.
        """
        return cls(
            Point.from_relative_coordinates(bbox.min_point, resolution),
            Point.from_relative_coordinates(bbox.max_point, resolution)
        )

    # TODO: Add intersections percentage, add check if point is inside or outside and bbox diff
