from __future__ import annotations

import typing
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy

from server.algorithms.data_types.image_typehint import CV_Image
from server.algorithms.data_types.point import Point


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
        return (self.mask * 255).astype(numpy.uint8)

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
