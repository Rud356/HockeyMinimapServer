from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

import cv2
import numpy as np

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
            self.x / resolution[0],
            self.y / resolution[1]
        )

    def visualize_point_on_image(
        self,
        image: np.ndarray,
        color: tuple[int, int, int] = (128, 38, 128),
        radius: int = 5
    ) -> np.ndarray:
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

        return cv2.circle(
            image,
            (int(self.x),
             int(self.y)),
            radius=radius,
            color=color,
            thickness=-1
        )

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
