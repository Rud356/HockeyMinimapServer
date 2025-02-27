from server.algorithms.data_types import Point
from server.algorithms.enums.camera_position import CameraPosition
from server.algorithms.enums.coordinate_split import HorizontalPosition, VerticalPosition
from server.utils.config.minimap_config import MinimapKeyPointConfig


class KeyPointPlacer:
    camera_position: CameraPosition
    minimap_key_points: MinimapKeyPointConfig

    def __init__(self, key_points: MinimapKeyPointConfig, camera_position: CameraPosition):
        self.minimap_key_points = key_points
        self.camera_position = camera_position

    def set_camera_position(self, camera_position: CameraPosition):
        self.camera_position = camera_position

    @staticmethod
    def determine_quadrant(point: Point, center_point: Point) -> tuple[HorizontalPosition, VerticalPosition]:
        """
        Определяет в каком квадранте находится точка относительно переданной центральной точки.

        :param center_point: Центральная точка, от которой начинается определение квадрантов в пространстве камеры.
        :param point: Точка, для которой определяется положение в квадранте.
        :return:
        """
        horizontal = HorizontalPosition.top if point.y < center_point.y else HorizontalPosition.bottom
        vertical = VerticalPosition.left if point.x < center_point.x else VerticalPosition.right
        return horizontal, vertical

    @staticmethod
    def flip_quadrant_horizontally(
        *quadrants: tuple[HorizontalPosition, VerticalPosition]
    ) -> list[tuple[HorizontalPosition, VerticalPosition]]:
        """
        Меняет местами верхние и нижние квадранты в пространстве для маппинга.

        :param quadrants: Квадранты для смены верха и низа.
        :return: Обновленные квадранты.
        """
        quadrants_match: dict[HorizontalPosition, HorizontalPosition] = {
            HorizontalPosition.top: HorizontalPosition.bottom,
            HorizontalPosition.bottom: HorizontalPosition.top,
            HorizontalPosition.center: HorizontalPosition.center
        }

        return [
            (quadrants_match[quadrant[0]], quadrant[1]) for quadrant in quadrants
        ]

    @staticmethod
    def flip_quadrant_vertically(
        *quadrants: tuple[HorizontalPosition, VerticalPosition]
    ) -> list[tuple[HorizontalPosition, VerticalPosition]]:
        """
        Меняет местами левые и верхние квадранты в пространстве для маппинга.

        :param quadrants: Квадранты для смены левой и правой стороны.
        :return: Обновленные квадранты.
        """
        quadrants_match: dict[VerticalPosition, VerticalPosition] = {
            VerticalPosition.left: VerticalPosition.right,
            VerticalPosition.right: VerticalPosition.left,
            VerticalPosition.center: VerticalPosition.center
        }

        return [
            (quadrant[0], quadrants_match[quadrant[1]]) for quadrant in quadrants
        ]
