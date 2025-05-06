from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy
import numpy as np
from numpy._typing import _32Bit, _64Bit

from server.algorithms.data_types.point import Point
from server.algorithms.data_types.image_typehint import CV_Image


@dataclass
class Mask:
    """
    Класс для хранения маски выделения из нейронной сети.
    """
    mask: CV_Image

    def visualize_mask(self) -> CV_Image:
        """
        Генерирует изображение маски.

        :return:
        """
        return self.mask.astype(numpy.uint8)

    def expand_mask(self, kernel: Optional[CV_Image] = None) -> Mask:
        """
        Увеличивает маску на 10 пикселей от текущего размера.

        :param kernel: Ядро в виде единичной матрицы увеличения размером (x, x)
            с нечетным числом больше 0 типа numpy.uint8.
        :return: Возвращает новую маску.
        """
        if kernel is None:
            # Expand mask by 10 pixels on each side
            kernel = numpy.ones((21, 21), numpy.uint8)

        new_mask: CV_Image = typing.cast(CV_Image, cv2.dilate(self.mask, kernel, iterations=1))
        return Mask(mask=new_mask)

    def check_points_are_in_mask_area(self, *points: Point) -> list[bool]:
        """
        Проверяет, находятся ли точки на маске, или нет.

        :param points: Точки в абсолютных координатах маски.
        :return: Список точек, находящихся в маске.
        """
        keep_list = [
            bool(self.mask[int(p.y)-1, int(p.x)-1] > 0) for p in points
        ]
        return keep_list

    def get_corners_of_mask(self) -> tuple[Point, Point]:
        """
        Получает координаты по углам маски.

        :return: Координаты верхней левой и нижней правой точки маски.
        """
        points:  numpy.ndarray[
            tuple[int, ...],
            numpy.dtype[numpy.signedinteger[_32Bit | _64Bit]]
        ] = np.argwhere(self.mask > 0)

        top_left_y, top_left_x = points.min(axis=0)
        bottom_right_y, bottom_right_x = points.max(axis=0)

        return Point(x=top_left_x, y=top_left_y), Point(x=bottom_right_x, y=bottom_right_y)

    @classmethod
    def from_multiple_masks(cls, *masks: CV_Image) -> Mask:
        """
        Генерирует объединенную маску из нескольких масок.

        :param masks: Маски в формате единиц или нулей единообразного размера.
        :return: Новая объединенная маска.
        :raise ValueError: Если передано меньше одной маски для объединения.
        """
        if len(masks) < 1:
            raise ValueError("Must provide at least 1 mask")

        return Mask(
            numpy.sum(
                numpy.ndarray(masks),
                axis=0
            ).astype(numpy.uint8)
        )
