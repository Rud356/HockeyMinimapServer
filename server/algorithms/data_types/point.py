from __future__ import annotations

import math
import typing
from typing import NamedTuple, TYPE_CHECKING

import cv2
import numpy as np

from server.algorithms.data_types.image_typehint import CV_Image
from server.algorithms.data_types.relative_point import RelativePoint

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

    def to_relative_coordinates(self, resolution: tuple[int, int]) -> RelativePoint:
        """
        Изменяет систему координат из абсолютной в относительную (значения от 0 до 1 в пространстве изображения).

        :param resolution: Размер изображения, в координатах которого получаем относительные координаты.
        :return: Ограничивающий прямоугольник в относительной системе координат.
        :raise ValueError: Если количество элементов в resolution не равно двум, или тип не int,
            или значения отрицательные, или ноль.
        """
        self.assert_resolution_validity(resolution)

        return RelativePoint(
            # Clipping points to space from 0 to 1
            max(min(self.x / resolution[0], 1), 0),
            max(min(self.y / resolution[1], 1), 0)
        )

    def to_relative_coordinates_inside_bbox(self, inside_of_bbox: BoundingBox) -> RelativePoint:
        """
        Вычисляет положение точки в рамках охватывающего прямоугольника.

        :param inside_of_bbox: Охватывающий прямоугольник, в рамках которого вычисляются относительные координаты.
        :return: Относительные координаты точки в рамках охватывающего прямоугольника.
        """
        clipped_point: Point = self.clip_point_to_bounding_box(inside_of_bbox)
        recalculated_clipped_point: Point = Point(
            clipped_point.x - inside_of_bbox.min_point.x,
            clipped_point.y - inside_of_bbox.min_point.y
        )
        recalculated_bottom_point: Point = Point(
            inside_of_bbox.max_point.x - inside_of_bbox.min_point.x,
            inside_of_bbox.max_point.y - inside_of_bbox.min_point.y
        )

        return recalculated_clipped_point.to_relative_coordinates(
            (int(recalculated_bottom_point.x), int(recalculated_bottom_point.y))
        )

    def visualize_point_on_image(
        self,
        image: CV_Image,
        color: tuple[int, int, int] = (128, 38, 128),
        radius: int = 5
    ) -> CV_Image:
        """
        Визуализирует точку на изображении.

        :param image: Изображение для визуализации.
        :param radius: Радиус изображения.
        :param color: Цвет круга.
        :return: Новое изображение с кругом.

        :raise ValueError: Неожиданный тип данных или значение меньше 1 для радиуса.
        """

        if not isinstance(radius, int) or radius < 1:
            raise ValueError("Unexpected value for radius: must be at least 1 with int type, "
                             f"(got {radius=})")

        return typing.cast(CV_Image,
            cv2.circle(
                image,
                (int(self.x), int(self.y)),
                radius=radius,
                color=color,
                thickness=-1
            )
        )

    def find_distance_from_point(self, other_point: tuple[float, float] | Point) -> float:
        """
        Находит расстояние от определенной точки до текущей точки.

        :param other_point: Точка, от которой ищем расстояние до текущей точки.
        :return: Расстояние до точки.
        """
        x1, y1 = self
        x2, y2 = other_point
        distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        return distance

    @classmethod
    def from_relative_coordinates(cls, point: RelativePoint, resolution: tuple[int, int]) -> Point:
        """
        Преобразует относительные координаты в абсолютные.

        :param point: Точка в относительных координатах.
        :param resolution: Размер изображения, в координатах которого получаем относительные координаты.
        :return: Точка в абсолютных координатах.
        :raise ValueError: Если количество элементов в resolution не равно двум, или тип не int,
            или значения отрицательные, или ноль.
        """
        cls.assert_resolution_validity(resolution)

        return cls(
            point.x * resolution[0],
            point.y * resolution[1]
        )

    @classmethod
    def from_relative_coordinates_inside_bbox(cls, point: RelativePoint, inside_of_bbox: BoundingBox) -> Point:
        recalculated_bottom_point: Point = Point(
            inside_of_bbox.max_point.x - inside_of_bbox.min_point.x,
            inside_of_bbox.max_point.y - inside_of_bbox.min_point.y
        )

        recalculated_clipped_point: Point = Point(
            (point.x * recalculated_bottom_point.x) + inside_of_bbox.min_point.x,
            (point.y * recalculated_bottom_point.y) + inside_of_bbox.min_point.y
        )

        return recalculated_clipped_point

    @staticmethod
    def assert_resolution_validity(resolution: tuple[int, int]) -> None:
        """
        Проверяет верность предоставленных координат.

        :param resolution: Размер изображения, в координатах которого получаем относительные координаты.
        :return: Нет возврата.
        :raise ValueError: Если количество элементов в resolution не равно двум, или тип не int,
            или значения отрицательные, или ноль.
        """
        if not isinstance(resolution, tuple):
            raise ValueError(f"Invalid type of resolution provided (got {type(resolution)})")

        if len(resolution) != 2:
            raise ValueError("Unexpected length of input tuple, must be 2 elements long")

        if not all(map(lambda v: isinstance(v, int) and v > 0, resolution)):
            raise ValueError("Must have all values of tuple of type int, and have value bigger than 0")
