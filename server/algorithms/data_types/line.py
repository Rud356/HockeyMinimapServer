from __future__ import annotations

import typing
from typing import NamedTuple, Optional, TYPE_CHECKING

import cv2

from server.algorithms.data_types.point import Point
from server.algorithms.data_types.image_typehint import CV_Image

if TYPE_CHECKING:
    from server.algorithms.data_types.bounding_box import BoundingBox


class Line(NamedTuple):
    """
    Представляет линию в двухмерном пространстве.
    """
    min_point: Point
    max_point: Point

    def visualize_line_on_image(
        self,
        image: CV_Image,
        color: tuple[int, int, int] = (0, 128, 196)
    ) -> CV_Image:
        """
        Визуализирует линию на изображении.

        :param color: Цвет линии.
        :param image: Исходное изображение.
        :return: Новое изображение.
        """
        return typing.cast(CV_Image,
            cv2.line(
                image,
                tuple(map(int, self.min_point)),
                tuple(map(int, self.max_point)),
                color,
                2,
                cv2.LINE_AA
            )
        )

    def clip_line_to_bounding_box(self, bounding_box: BoundingBox) -> Line:
        """
        Вписывает линию в ограничивающий прямоугольник.

        :param bounding_box: Ограничивающий прямоугольник.
        :return: Новая линия.
        """
        return Line(
            self.min_point.clip_point_to_bounding_box(bounding_box),
            self.max_point.clip_point_to_bounding_box(bounding_box)
        )

    @classmethod
    def find_lines(
        cls,
        image: CV_Image
    ) -> Optional[Line]:
        """
        Находит линию на изображении с помощью алгоритма Hough Line из OpenCV.

        :param image: Исходное изображение с выделенными границами.
        :return: Искомая линия, проходящая через точки на изображении или ничего.
        """
        image = typing.cast(CV_Image, cv2.Canny(image, 50.0, 200.0))
        contours, hierarchy = cv2.findContours(image, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        if len(contours) < 1:
            return None

        cnt = contours[0]
        rows, cols = image.shape[:2]
        [vx, vy, x, y] = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01)
        lefty = int((-x * vy / vx) + y)
        righty = int(((cols - x) * vy / vx) + y)
        return cls(Point(cols-1, righty), Point(0, lefty))
