from __future__ import annotations

from typing import NamedTuple, Optional, TYPE_CHECKING

import cv2
import numpy

from server.algorithms.data_types.point import Point

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
        image: numpy.ndarray,
        color: tuple[int, int, int] = (0, 128, 196)
    ) -> numpy.ndarray:
        """
        Визуализирует линию на изображении.

        :param color: Цвет линии.
        :param image: Исходное изображение.
        :return: Новое изображение.
        """
        return cv2.line(
            image,
            tuple(map(int, self.min_point)),
            tuple(map(int, self.max_point)),
            color,
            2,
            cv2.LINE_AA
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
        image: numpy.ndarray,
        min_threshold: int = 1,
        max_threshold: int = 1000
    ) -> Optional[Line]:
        """
        Находит линию на изображении с помощью алгоритма Hough Line из OpenCV.

        :param image: Исходное изображение с выделенными границами.
        :param min_threshold: Минимальный параметр границы.
        :param max_threshold: Максимальный параметр границы.

        :return: Искомая линия, проходящая через точки на изображении.
        """
        image = cv2.Canny(image.copy(), 100, 200)

        assert min_threshold > 0, ("Минимальное пороговое значение алгоритма преобразования Хафа "
                                   "должно быть не меньше 1")

        while min_threshold <= max_threshold:
            base_threshold = (min_threshold + max_threshold) // 2
            lines = cv2.HoughLines(image, 1., numpy.pi / 180, base_threshold, None, 0)

            if lines is None:
                max_threshold = base_threshold - 1

            elif len(lines) > 2:
                min_threshold = base_threshold + 1

            else:
                # Выделена единственная линия
                (r, theta) = lines[:, 0][0]
                a = numpy.cos(theta)
                b = numpy.sin(theta)

                x0 = a * r
                y0 = b * r

                point1, point2 = sorted([
                    Point(int(x0 + 1000 * (-b)), int(y0 + 1000 * a)),
                    Point(int(x0 - 1000 * (-b)), int(y0 - 1000 * a))
                ])

                return Line(point1, point2)

        # Линия не найдена
        return None
