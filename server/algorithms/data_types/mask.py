from __future__ import annotations
from typing import Optional
from dataclasses import dataclass

import cv2
import numpy


@dataclass
class Mask:
    """
    Класс для хранения маски выделения из нейронной сети.
    """
    mask: numpy.ndarray

    def visualize_mask(self) -> numpy.ndarray:
        """
        Генерирует изображение маски.

        :return:
        """
        return (self.mask * 255).astype(numpy.uint8)

    def expand_mask(self, kernel: Optional[numpy.ndarray] = None) -> Mask:
        """
        Увеличивает маску на 10 пикселей от текущего размера.

        :param kernel: Ядро в виде единичной матрицы увеличения размером (x, x)
            с нечетным числом больше 0 типа numpy.uint8.
        :return: Возвращает новую маску.
        """
        if kernel is None:
            # Expand mask by 10 pixels on each side
            kernel = numpy.ones((21, 21), numpy.uint8)

        new_mask = cv2.dilate(self.mask, kernel, iterations=1)
        return Mask(mask=new_mask)

    @classmethod
    def from_multiple_masks(cls, *masks: numpy.ndarray) -> Mask:
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
                numpy.ndarray[masks],
                axis=0
            ).astype(numpy.uint8)
        )
