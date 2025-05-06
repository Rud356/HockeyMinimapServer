import typing
from typing import Mapping

import cv2
import numpy

from server.algorithms.data_types import BoundingBox, CV_Image, Point, RelativePoint
from server.algorithms.exceptions.not_enough_field_points import NotEnoughFieldPoints
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.utils.config.key_point import KeyPoint


class PlayersMapper:
    """
    Класс для реализации алгоритма соотнесения координат игроков из видео с координатами игроков на мини-карте.
    """
    field_transform: numpy.ndarray

    def __init__(
        self,
        map_bbox: BoundingBox,
        field_points: Mapping[KeyPoint | RelativePointDTO, Point | RelativePointDTO],
        reproj_threshold: float = 4.0,
        max_iters: int = 2000,
        confidence: float = 0.9
    ):
        if len(field_points.keys()) < 4:
            raise NotEnoughFieldPoints("Not enough tracking points")

        self.map_bbox = map_bbox
        src_points = numpy.array([[pt.x, pt.y] for kp, pt in field_points.items()], dtype='float32')
        dst_pts = numpy.array([[kp.x, kp.y] for kp, pt in field_points.items()], dtype='float32')

        homography_transform, status = cv2.findHomography(
            src_points, dst_pts, cv2.RANSAC, reproj_threshold, maxIters=max_iters, confidence=confidence
        )

        self.field_transform = homography_transform

    def warp_image(self, image: CV_Image) -> CV_Image:
        """
        Искажает изображение для демонстрации получаемого преобразования.

        :param image: Изменяемое изображение.
        :return: Новое изображение с примененным преобразованием.
        """
        height, width = image.shape[:2]

        scale_matrix: numpy.ndarray = numpy.array(
            [
                [width, 0, 0],
                [0, height, 0],
                [0, 0, 1]
            ],
            dtype = 'float32'
        )
        adjusted_transform = scale_matrix @ self.field_transform @ numpy.linalg.inv(scale_matrix)

        return typing.cast(
            CV_Image, cv2.warpPerspective(
                image,
                adjusted_transform,
                (width, height),
                flags = cv2.INTER_CUBIC
            )
        )

    def transform_point_to_minimap_coordinates(self, *points: RelativePoint | RelativePointDTO) -> list[RelativePoint]:
        """
        Конвертирует точки из пространства камеры в пространство мини-карты.

        :param points: Координаты игроков.
        :return: Координаты игроков в мини-карте.
        """
        if len(points) == 0:
            return []

        pts: numpy.ndarray = numpy.array([[p.x, p.y] for p in points], dtype='float32')
        pts_converted: numpy.ndarray = numpy.array([pts])
        to_map_coordinates = cv2.perspectiveTransform(pts_converted, self.field_transform)[0]

        return [
            RelativePoint(*Point(x, y).clip_point_to_bounding_box(self.map_bbox))
            for x, y in to_map_coordinates
        ]
