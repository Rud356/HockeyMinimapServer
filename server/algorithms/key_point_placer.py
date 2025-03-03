from typing import TypeAlias

from server.algorithms.data_types import Point
from server.algorithms.enums.camera_position import CameraPosition
from server.algorithms.enums.coordinate_split import HorizontalPosition, VerticalPosition
from server.utils.config.key_point import KeyPoint
from server.utils.config.minimap_config import MinimapKeyPointConfig


PointQuadrant: TypeAlias = tuple[HorizontalPosition, VerticalPosition]

class KeyPointPlacer:
    camera_position: CameraPosition
    minimap_key_points: MinimapKeyPointConfig
    resolution: tuple[int, int]

    def __init__(self, key_points: MinimapKeyPointConfig, camera_position: CameraPosition, resolution: tuple[int, int]):
        self.minimap_key_points = key_points
        self.camera_position = camera_position

        if (
            resolution is None or
            len(resolution) != 2 or
                (resolution[0] < 0 or resolution[1] < 0) or
            any(map(lambda v: not isinstance(resolution, int), resolution))
        ):
            raise ValueError("Must provide valid resolution")

        self.resolution = resolution

        # Mapping for center line points (in map space)
        self.center_line_points: dict[PointQuadrant, KeyPoint] = {
            (HorizontalPosition.top, VerticalPosition.left): MinimapKeyPointConfig.center_line_top,
            (HorizontalPosition.top, VerticalPosition.right): MinimapKeyPointConfig.center_line_top,
            (HorizontalPosition.bottom, VerticalPosition.left): MinimapKeyPointConfig.center_line_bottom,
            (HorizontalPosition.bottom, VerticalPosition.right): MinimapKeyPointConfig.center_line_bottom
        }

        # Mapping by default work for top points of lines in camera space, other points figured out by relating to the
        # top point of it according to bottom point
        # Mapping for blue lines
        self.blue_lines_points: dict[PointQuadrant, KeyPoint] = {
            (HorizontalPosition.top, VerticalPosition.left): MinimapKeyPointConfig.left_blue_line_top,
            (HorizontalPosition.top, VerticalPosition.right): MinimapKeyPointConfig.right_blue_line_top,
            (HorizontalPosition.bottom, VerticalPosition.left): MinimapKeyPointConfig.left_blue_line_bottom,
            (HorizontalPosition.bottom, VerticalPosition.right): MinimapKeyPointConfig.right_blue_line_bottom
        }

        # Mapping for red circles
        self.red_circles_points: dict[PointQuadrant, KeyPoint] = {
            (HorizontalPosition.top, VerticalPosition.left): MinimapKeyPointConfig.red_circle_top_left,
            (HorizontalPosition.top, VerticalPosition.right): MinimapKeyPointConfig.red_circle_top_right,
            (HorizontalPosition.bottom, VerticalPosition.left): MinimapKeyPointConfig.red_circle_bottom_left,
            (HorizontalPosition.bottom, VerticalPosition.right): MinimapKeyPointConfig.red_circle_bottom_right
        }

        # Mapping goal zones
        self.goal_zones_points: dict[PointQuadrant, KeyPoint] = {
            (HorizontalPosition.top, VerticalPosition.left): MinimapKeyPointConfig.left_goal_zone,
            (HorizontalPosition.top, VerticalPosition.right): MinimapKeyPointConfig.right_goal_zone,
            (HorizontalPosition.bottom, VerticalPosition.left): MinimapKeyPointConfig.left_goal_zone,
            (HorizontalPosition.bottom, VerticalPosition.right): MinimapKeyPointConfig.right_goal_zone
        }

    def set_camera_position(self, camera_position: CameraPosition):
        """
        Устанавливает положение камеры на поле.

        :param camera_position: Положение камеры относительно поля.
        :return: Нет возврата.
        """
        self.camera_position = camera_position

    def get_fake_anchor_center_point(self):
        pass

    def map_blue_circles_to_key_points(self, *blue_circles: Point, center_point: Point) -> dict[KeyPoint, Point]:
        """
        Сопоставляет положения синих кругов с положениями на мини-карте.

        :param blue_circles: Точки синих кругов.
        :param center_point: Центральная опорная точка.
        :return: Соотнесение ключевых точек поля и точек на видео.
        """
        quadrants: list[PointQuadrant] = [
            self.determine_quadrant(blue_circle, center_point) for blue_circle in blue_circles
        ]

        if self.camera_position in {
            CameraPosition.top_left_corner,
            CameraPosition.top_middle_point,
            CameraPosition.top_right_corner
        }:
            quadrants = list(self.flip_quadrant_horizontally(*quadrants))

        # TODO: add rotations for camera positions on sides of field
        mapped_points: dict[KeyPoint, Point] = {
            self.blue_lines_points[quadrant]: point for quadrant, point in zip(quadrants, blue_circles)
        }

        return mapped_points

    def map_goal_zones_to_key_points(self, *goal_zones: Point, center_point: Point) -> dict[KeyPoint, Point]:
        """
        Соотносит положение зон с мини-картой.

        :param goal_zones: Зоны гола в виде точек центров.
        :param center_point: Центральная точка поля.
        :return: Соотнесение ключевых точек и точек на видео.
        """
        quadrants: list[PointQuadrant] = [
            self.determine_quadrant(goal_zone, center_point) for goal_zone in goal_zones
        ]

        mapped_to: dict[KeyPoint, Point] = {
            self.goal_zones_points[quadrant]: point for quadrant, point in zip(quadrants, goal_zones)
        }

        return mapped_to

    # TODO: add mapping for blue lines and for goal zones lines

    # TODO: add generating fake key points from resolution and camera and between points

    @staticmethod
    def determine_quadrant(point: Point, center_point: Point) -> PointQuadrant:
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
        *quadrants: PointQuadrant
    ) -> list[PointQuadrant]:
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
        *quadrants: PointQuadrant
    ) -> list[PointQuadrant]:
        """
        Меняет местами левые и верхние квадранты в пространстве для маппинга на мини-карту из пространства камеры.

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

    @staticmethod
    def rotate_quadrants_left(
        *quadrants: PointQuadrant
    ) -> list[PointQuadrant]:
        """
        Поворачивает квадранты влево относительно камеры в пространство мини-карты.

        :param quadrants: Квадранты для поворота.
        :return: Обновленные квадранты.
        """
        quadrants_match: dict[
            tuple[HorizontalPosition, VerticalPosition],
            tuple[HorizontalPosition, VerticalPosition]
        ] = {
            (HorizontalPosition.center, VerticalPosition.center): (HorizontalPosition.center, VerticalPosition.center),
            (HorizontalPosition.top, VerticalPosition.right): (HorizontalPosition.top, VerticalPosition.left),
            (HorizontalPosition.top, VerticalPosition.left): (HorizontalPosition.bottom, VerticalPosition.right),
            (HorizontalPosition.bottom, VerticalPosition.right): (HorizontalPosition.top, VerticalPosition.right),
            (HorizontalPosition.bottom, VerticalPosition.left): (HorizontalPosition.bottom, VerticalPosition.right)
        }

        return [
            quadrants_match[quadrant[0], quadrant[1]] for quadrant in quadrants
        ]

    @staticmethod
    def rotate_quadrants_right(
        *quadrants: PointQuadrant
    ) -> list[PointQuadrant]:
        """
        Поворачивает квадранты вправо относительно камеры в пространство мини-карты.

        :param quadrants: Квадранты для поворота.
        :return: Обновленные квадранты.
        """
        quadrants_match: dict[
            PointQuadrant,
            PointQuadrant
        ] = {
            (HorizontalPosition.center, VerticalPosition.center): (HorizontalPosition.center, VerticalPosition.center),
            (HorizontalPosition.top, VerticalPosition.right): (HorizontalPosition.bottom, VerticalPosition.right),
            (HorizontalPosition.top, VerticalPosition.left): (HorizontalPosition.top, VerticalPosition.right),
            (HorizontalPosition.bottom, VerticalPosition.right): (HorizontalPosition.bottom, VerticalPosition.left),
            (HorizontalPosition.bottom, VerticalPosition.left): (HorizontalPosition.top, VerticalPosition.left)
        }

        return [
            quadrants_match[quadrant[0], quadrant[1]] for quadrant in quadrants
        ]
