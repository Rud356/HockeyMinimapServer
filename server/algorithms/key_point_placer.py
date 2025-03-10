import math
import numpy
from typing import Optional, TypeAlias

from server.algorithms.data_types import Point, Line
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
            not all(map(lambda v: not isinstance(resolution, int), resolution))
        ):
            raise ValueError("Must provide valid resolution")

        self.resolution = resolution

        # Mapping for center line points (in map space)
        self.center_line_points: dict[PointQuadrant, KeyPoint] = {
            (HorizontalPosition.top, VerticalPosition.left): key_points.center_line_top,
            (HorizontalPosition.top, VerticalPosition.right): key_points.center_line_top,
            (HorizontalPosition.bottom, VerticalPosition.left): key_points.center_line_bottom,
            (HorizontalPosition.bottom, VerticalPosition.right): key_points.center_line_bottom
        }

        # Mapping by default work for top points of lines in camera space, other points figured out by relating to the
        # top point of it according to bottom point
        # Mapping for blue lines
        self.blue_lines_points: dict[PointQuadrant, KeyPoint] = {
            (HorizontalPosition.top, VerticalPosition.left): key_points.left_blue_line_top,
            (HorizontalPosition.top, VerticalPosition.right): key_points.right_blue_line_top,
            (HorizontalPosition.bottom, VerticalPosition.left): key_points.left_blue_line_bottom,
            (HorizontalPosition.bottom, VerticalPosition.right): key_points.right_blue_line_bottom
        }

        # Mapping for red circles
        self.red_circles_points: dict[PointQuadrant, KeyPoint] = {
            (HorizontalPosition.top, VerticalPosition.left): key_points.red_circle_top_left,
            (HorizontalPosition.top, VerticalPosition.right): key_points.red_circle_top_right,
            (HorizontalPosition.bottom, VerticalPosition.left): key_points.red_circle_bottom_left,
            (HorizontalPosition.bottom, VerticalPosition.right): key_points.red_circle_bottom_right
        }

        # Mapping goal zones
        self.goal_zones_points: dict[PointQuadrant, KeyPoint] = {
            (HorizontalPosition.top, VerticalPosition.left): key_points.left_goal_zone,
            (HorizontalPosition.top, VerticalPosition.right): key_points.right_goal_zone,
            (HorizontalPosition.bottom, VerticalPosition.left): key_points.left_goal_zone,
            (HorizontalPosition.bottom, VerticalPosition.right): key_points.right_goal_zone
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

    def map_red_circles_to_key_points(self, *blue_circles: Point, center_point: Point) -> dict[KeyPoint, Point]:
        """
        Сопоставляет положения синих кругов с положениями на мини-карте.

        :param blue_circles: Точки синих кругов.
        :param center_point: Центральная опорная точка.
        :return: Соотнесение ключевых точек поля и точек на видео.
        """
        quadrants: list[PointQuadrant] = [
            self.determine_quadrant(blue_circle, center_point) for blue_circle in blue_circles
        ]
        quadrants = self.apply_camera_rotation_on_quadrants(*quadrants)

        # TODO: add rotations for camera positions on sides of field
        mapped_points: dict[KeyPoint, Point] = {
            self.red_circles_points[quadrant]: point for quadrant, point in zip(quadrants, blue_circles)
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
        quadrants = self.apply_camera_rotation_on_quadrants(*quadrants)

        mapped_to: dict[KeyPoint, Point] = {
            self.goal_zones_points[quadrant]: point for quadrant, point in zip(quadrants, goal_zones)
        }

        return mapped_to

    def map_blue_lines_to_key_points(self, *blue_lines: Line, center_point: Point) -> dict[KeyPoint, Point]:
        quadrants: list[PointQuadrant] = [
            # Determines the upper left points quadrant of a whole line
            self.determine_quadrant(blue_line.min_point, center_point) for blue_line in blue_lines
        ]
        quadrants = self.apply_camera_rotation_on_quadrants(*quadrants)

        mapped_points: dict[KeyPoint, Point] = {}

        for line, quadrant in zip(blue_lines, quadrants):
            mapped_points[self.blue_lines_points[quadrant]] = line.min_point
            opposite_point_quadrant, *_ = self.flip_quadrant_horizontally(quadrant)

            mapped_points[
                self.blue_lines_points[opposite_point_quadrant]
            ] = line.max_point

        return mapped_points

    def map_goal_lines(self, *goal_lines: Line, center_point: Point) -> dict[KeyPoint, Point]:
        """
        Распределяет линии зоны гола по полю.

        :param goal_lines: Линии зоны гола (от 1 до 4 штук).
        :param center_point: Центральная опорная точка для алгоритма.
        :return: Соотнесения точек.
        :raise ValueError: Неожиданное количество линий для алгоритма.
        """
        if not (0 < len(goal_lines) < 5):
            raise ValueError("Expect from 1 to 4 lines as input")

        quadrants_min: list[PointQuadrant] = [
            # Determines the upper left points quadrant of a whole line
            self.determine_quadrant(goal_line.min_point, center_point) for goal_line in goal_lines
        ]
        quadrants_min = self.apply_camera_rotation_on_quadrants(*quadrants_min)

        quadrants_max: list[PointQuadrant] = [
            # Determines the upper left points quadrant of a whole line
            self.determine_quadrant(goal_line.max_point, center_point) for goal_line in goal_lines
        ]
        quadrants_max = self.apply_camera_rotation_on_quadrants(*quadrants_max)

        points_to_map: list[tuple[Line, PointQuadrant, PointQuadrant]] = [
            (line, max_point_quadrant, min_point_quadrant)
            for line, max_point_quadrant, min_point_quadrant in
                zip(goal_lines, quadrants_max, quadrants_min)
        ]
        points_to_map.sort(
            key=lambda v: math.sqrt(v[0].min_point.x ** 2 + v[0].min_point.y ** 2)
        )

        left_lines: list[
            tuple[Line, PointQuadrant, PointQuadrant]
        ] = [
            (line, max_point_quadrant, min_point_quadrant)
            for line, max_point_quadrant, min_point_quadrant in points_to_map
                if min_point_quadrant[1] == VerticalPosition.left
        ]
        right_lines: list[
            tuple[Line, PointQuadrant, PointQuadrant]
        ] = [
            (line, max_point_quadrant, min_point_quadrant)
            for line, max_point_quadrant, min_point_quadrant in points_to_map
                if min_point_quadrant[1] == VerticalPosition.right
        ]

        used_lines: list[tuple[Line, PointQuadrant, PointQuadrant]] = []
        left_line: Optional[Line] = None
        if left_lines and len(left_lines) == 2:
            used_lines.extend(left_lines)
            left_line = self.combine_points_to_line(left_lines)

        right_line: Optional[Line] = None
        if right_lines and len(right_lines) == 2:
            used_lines.extend(right_lines)
            right_line = self.combine_points_to_line(right_lines)

        key_points_mapping = {
            (HorizontalPosition.top, VerticalPosition.left): self.minimap_key_points.left_goal_line_top,
            (HorizontalPosition.bottom, VerticalPosition.left): self.minimap_key_points.left_goal_line_after_zone_bottom,
            (HorizontalPosition.top, VerticalPosition.right): self.minimap_key_points.right_goal_line_top,
            (HorizontalPosition.bottom, VerticalPosition.right): self.minimap_key_points.right_goal_line_after_zone_bottom
        }

        line_points_quadrants: dict[PointQuadrant, Point] = {}
        for line in filter(None, (left_line, right_line)):
            for point in (line.min_point, line.max_point):
                key_point, *_ = self.apply_camera_rotation_on_quadrants(
                    self.determine_quadrant(point, center_point=center_point)
                )
                line_points_quadrants[key_point] = point

        mapped_points: dict[KeyPoint, Point] = {
            key_points_mapping[k]: v for k, v in line_points_quadrants.items()
        }

        mapped_points |= self.match_paired_lines_key_points(goal_lines, mapped_points)

        leftover_lines: set[
            tuple[Line, PointQuadrant, PointQuadrant]
        ] = (set(left_lines) | set(right_lines)) - set(used_lines)

        for leftover_line, min_quadrant, max_quadrant in leftover_lines:
            tmp_line: Line


            if left_line:
                tmp_line = Line(
                    line_points_quadrants[HorizontalPosition.top, VerticalPosition.left],
                    line_points_quadrants[HorizontalPosition.bottom, VerticalPosition.left]
                )

            elif right_line:
                tmp_line = Line(
                    line_points_quadrants[HorizontalPosition.top, VerticalPosition.right],
                    line_points_quadrants[HorizontalPosition.bottom, VerticalPosition.right]
                )

            else:
                bottom_point, upper_point = sorted(
                    [leftover_line.min_point, leftover_line.max_point],
                    key=lambda p: p.find_distance_from_point(center_point)
                )
                tmp_line = Line(upper_point, bottom_point)

            l1, l2 = leftover_line, tmp_line
            (x1, y1), (x2, y2) = l1[0], l1[1]
            (u1, v1), (u2, v2) = l2[0], l2[1]
            vec1 = numpy.array([x2 - x1, y2 - y1])
            vec2 = numpy.array([u2 - u1, v2 - v1])
            dot_product = numpy.dot(vec1, vec2)

            if dot_product >= 0:
                mapped_points[key_points_mapping[min_quadrant]] = leftover_line.min_point
            else:
                mapped_points[key_points_mapping[max_quadrant]] = leftover_line.max_point

            mapped_points |= self.match_paired_lines_key_points((leftover_line,), mapped_points)

        return mapped_points

    # TODO: add generating fake key points from resolution and camera and between points
    def apply_camera_rotation_on_quadrants(self, *quadrants: PointQuadrant) -> list[PointQuadrant]:
        """
        Применяет трансформацию к квадрантам для перевода из квадрантов камеры в квадранты мини-карты.

        :param quadrants: Квадранты для приведения.
        :return: Приведенные квадранты.
        """
        modified_quadrants = list(quadrants)

        if self.camera_position in {
            CameraPosition.top_left_corner,
            CameraPosition.top_middle_point,
            CameraPosition.top_right_corner
        }:
            modified_quadrants = list(
                self.flip_quadrant_vertically(
                    *self.flip_quadrant_horizontally(*quadrants)
                )
            )

        if self.camera_position == CameraPosition.right_side_camera:
            modified_quadrants = list(self.rotate_quadrants_left(*quadrants))

        elif self.camera_position == CameraPosition.left_side_camera:
            modified_quadrants = list(self.rotate_quadrants_right(*quadrants))

        return modified_quadrants

    def match_paired_lines_key_points(
        self, goal_lines: tuple[Line, ...], mapped_points: dict[KeyPoint, Point]
    ) -> dict[KeyPoint, Point]:
        """
        Подбирает пары для точек, не использованных в распределении линий.

        :param goal_lines: Линии зоны гола.
        :param mapped_points: Соотнесенные точки.
        :return: Новый словарь дополнительно соотнесенных точек.
        """
        unused_line_points_mapping = {
            self.minimap_key_points.left_goal_line_top: self.minimap_key_points.left_goal_line_bottom,
            self.minimap_key_points.left_goal_line_after_zone_top: self.minimap_key_points.left_goal_line_after_zone_bottom,
            self.minimap_key_points.left_goal_line_after_zone_bottom: self.minimap_key_points.left_goal_line_after_zone_top,
            self.minimap_key_points.right_goal_line_top: self.minimap_key_points.right_goal_line_bottom,
            self.minimap_key_points.right_goal_line_after_zone_top: self.minimap_key_points.right_goal_line_after_zone_bottom,
            self.minimap_key_points.right_goal_line_after_zone_bottom: self.minimap_key_points.right_goal_line_after_zone_top
        }
        mapped_new_points: dict[KeyPoint, Point] = {}

        # Map unused line points
        for line in goal_lines:
            # Get all lines point
            used_point: Point
            unused_point: Point

            if line.min_point not in mapped_points.values():
                used_point = line.max_point
                unused_point = line.min_point

            elif line.max_point not in mapped_points.values():
                used_point = line.min_point
                unused_point = line.max_point

            else:
                # Can't map, something gone wrong
                continue

            for key_point, point in mapped_points.items():
                if point == used_point:
                    new_key_point = unused_line_points_mapping[key_point]
                    mapped_new_points[new_key_point] = unused_point
                    break

        return mapped_new_points

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

    @staticmethod
    def combine_points_to_line(lines: list[tuple[Line, PointQuadrant, PointQuadrant]]) -> Line:
        """
        Combines points from lines to create a new line.

        :param lines: Lines to combine.
        :return: Combined line.
        """
        min_points = [line.min_point for line, _, _ in lines]
        max_points = [line.max_point for line, _, _ in lines]

        combined_min_point = min(min_points, key=lambda p: math.sqrt(p.x ** 2 + p.y ** 2))
        combined_max_point = max(max_points, key=lambda p: math.sqrt(p.x ** 2 + p.y ** 2))

        return Line(combined_min_point, combined_max_point)
