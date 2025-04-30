import itertools
import math
from typing import Optional, TypeAlias

from server.algorithms.data_types import BoundingBox, Line, Point
from server.algorithms.enums.camera_position import CameraPosition
from server.algorithms.enums.coordinate_split import HorizontalPosition, VerticalPosition
from server.algorithms.exceptions.anchor_point_required import AnchorPointRequired
from server.utils.config.key_point import KeyPoint
from server.utils.config.minimap_config import MinimapKeyPointConfig

PointQuadrant: TypeAlias = tuple[HorizontalPosition, VerticalPosition]

class KeyPointPlacer:
    """
    Класс для автоматизации расположения точек по полю исходят из предоставленных данных.
    """
    camera_position: CameraPosition
    minimap_key_points: MinimapKeyPointConfig
    resolution: tuple[int, int]

    def __init__(
        self,
        key_points: MinimapKeyPointConfig,
        camera_position: CameraPosition,
        resolution: tuple[int, int]
    ):
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

    def set_camera_position(self, camera_position: CameraPosition) -> None:
        """
        Устанавливает положение камеры на поле.

        :param camera_position: Положение камеры относительно поля.
        :return: Нет возврата.
        """
        self.camera_position = camera_position

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
        """
        Соотносит точки синих линий с точками на карте.

        :param blue_lines: Синие линии.
        :param center_point: Центральная точка.
        :return: Соотнесение синих линий с точками на мини-карте.
        """
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
            # Determines the bottom right points quadrant of a whole line
            self.determine_quadrant(goal_line.max_point, center_point) for goal_line in goal_lines
        ]
        quadrants_max = self.apply_camera_rotation_on_quadrants(*quadrants_max)

        points_to_map: list[tuple[Line, PointQuadrant, PointQuadrant]] = [
            (line, max_point_quadrant, min_point_quadrant)
            for line, max_point_quadrant, min_point_quadrant in
                zip(goal_lines, quadrants_max, quadrants_min)
        ]
        # Order by distance from 0, 0
        points_to_map.sort(
            key=lambda v: math.sqrt(v[0].min_point.x ** 2 + v[0].min_point.y ** 2)
        )

        # All lines on left side of field
        left_lines: list[
            tuple[Line, PointQuadrant, PointQuadrant]
        ] = [
            (line, max_point_quadrant, min_point_quadrant)
            for line, max_point_quadrant, min_point_quadrant in points_to_map
                if min_point_quadrant[1] == VerticalPosition.left
        ]

        # All lines on right side of field
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

        # Long lines point mapping
        key_points_mapping = {
            (HorizontalPosition.top, VerticalPosition.left): self.minimap_key_points.left_goal_line_top,
            (HorizontalPosition.bottom, VerticalPosition.left): self.minimap_key_points.left_goal_line_after_zone_bottom,
            (HorizontalPosition.top, VerticalPosition.right): self.minimap_key_points.right_goal_line_top,
            (HorizontalPosition.bottom, VerticalPosition.right): self.minimap_key_points.right_goal_line_after_zone_bottom
        }

        line_points_quadrants: dict[PointQuadrant, Point] = {}
        for line in filter(None, (left_line, right_line)):
            for point in (line.min_point, line.max_point):
                # Map a point out of the line to some quadrant on map
                key_point, *_ = self.apply_camera_rotation_on_quadrants(
                    self.determine_quadrant(point, center_point=center_point)
                )
                line_points_quadrants[key_point] = point

        # Map points to actual positions of key points
        mapped_points: dict[KeyPoint, Point] = {
            key_points_mapping[k]: v for k, v in line_points_quadrants.items()
        }

        # Map to complementary points
        mapped_points |= self.match_paired_lines_key_points(goal_lines, mapped_points)

        # Find all lines that didn't have any pair and wasn't used
        leftover_lines: set[
            tuple[Line, PointQuadrant, PointQuadrant]
        ] = (set(left_lines) | set(right_lines)) - set(used_lines)

        for leftover_line, min_quadrant, max_quadrant in leftover_lines:
            # If min points is further away from center point - safe to assume it is top
            if leftover_line.min_point.find_distance_from_point(
                    (center_point.x, center_point.y)
            ) > leftover_line.max_point.find_distance_from_point(
                (center_point.x, center_point.y)
            ):
                mapped_points[key_points_mapping[min_quadrant]] = leftover_line.min_point

            else:
                mapped_points[key_points_mapping[max_quadrant]] = leftover_line.max_point

            # Match complementary point of leftover point in line
            mapped_points |= self.match_paired_lines_key_points((leftover_line,), mapped_points)

        return mapped_points

    def map_blue_circle_point(self, circle_point: Point) -> dict[KeyPoint, Point]:
        """
        Соотносит точку центрального круга с точкой на мини-карте.

        :param circle_point: Точка центра круга.
        :return: Соотнесение центральной точки круга на мини-карте и на камере.
        """
        return {self.minimap_key_points.center_circle: circle_point}

    def map_red_line_to_key_points(self, red_line: Line, center_point: Point) -> dict[KeyPoint, Point]:
        """
        Соотносит точки центральной линии с точками на мини-карте.

        :param red_line: Красная линия.
        :param center_point: Точка центра.
        :return: Соотнесение точек красной линии к точкам мини-карты.
        """
        quadrants: list[tuple[PointQuadrant, Point]] = [
            (self.apply_camera_rotation_on_quadrants(self.determine_quadrant(p, center_point))[0], p)
            for p in (red_line.max_point, red_line.min_point)
        ]

        quadrants_mapping: dict[HorizontalPosition, KeyPoint] = {
            HorizontalPosition.top: self.minimap_key_points.center_line_top,
            HorizontalPosition.bottom: self.minimap_key_points.center_line_bottom
        }

        for n, quadrant in enumerate(quadrants):
            # Check if both points on opposite sides
            if quadrant[0][0] in map(lambda q: q[0][0], quadrants[:n] + quadrants[n+1:]):
                break

        else:
            # Points are on opposite sides
            return {
                quadrants_mapping[quadrant[0]]: p for quadrant, p in quadrants
            }

        if self.camera_position not in {
            CameraPosition.right_side_camera,
            CameraPosition.top_left_corner,
            CameraPosition.top_middle_point,
            CameraPosition.top_right_corner
        }:
            # Not flipped orientation since in those - the points that are close to center are closer to 0, 0 as well
            return {
                quadrants_mapping[HorizontalPosition.top]: red_line.min_point,
                quadrants_mapping[HorizontalPosition.bottom]: red_line.max_point
            }

        else:
            # Flipped since points are on opposite side of field when counted from 0, 0 to the minimap coordinates
            return {
                quadrants_mapping[HorizontalPosition.bottom]: red_line.min_point,
                quadrants_mapping[HorizontalPosition.top]: red_line.max_point
            }

    def map_to_key_points(
        self,
        field: BoundingBox,
        anchor_center_point: Optional[Point] = None,
        blue_circle_center: Optional[Point] = None,
        center_line: Optional[Line] = None,
        red_circle_centers: Optional[tuple[Point, ...]] = None,
        blue_lines: Optional[tuple[Line, ...]] = None,
        goal_zones_centers: Optional[tuple[Point, ...]] = None,
        goal_lines: Optional[tuple[Line, ...]] = None
    ) -> dict[KeyPoint, Point]:
        """
        Соотносит переданные точки и линии в координаты мини-карты.

        :param field: Охватывающий прямоугольник поля.
        :param anchor_center_point: Пользовательская поддерживающая центральная точка.
        :param blue_circle_center: Точка центра от синего центрального круга.
        :param center_line: Центральная линия.
        :param red_circle_centers: Точки центров красных кругов.
        :param blue_lines: Синие линии.
        :param goal_zones_centers: Точки центров зон гола.
        :param goal_lines: Линии от зоны гола.
        :return: Соотнесение ключевых точек на мини-карте к точкам с камеры.
        :raise AnchorPointRequired: Если не была передана точка, являющаяся центральной для поля,
            и не удалось её вычислить.
        """

        # Calculating alternatively
        resulting_mapping: dict[KeyPoint, Point] = {}
        final_anchor_point: Optional[Point] = None

        if blue_circle_center is not None:
            final_anchor_point = blue_circle_center
            # TODO: Check if point needs to be dropped because of touching side of field
            resulting_mapping[self.minimap_key_points.center_circle] = blue_circle_center

        if anchor_center_point is not None:
            final_anchor_point = anchor_center_point

        if final_anchor_point is None:
            # TODO: Calculate fake center point
            pass

        if final_anchor_point is None:
            raise AnchorPointRequired("The anchor point is required to keep algorithm working")

        if center_line is not None:
            # TODO: Check if some points needs to be dropped because of touching side of field
            resulting_mapping |= self.map_red_line_to_key_points(center_line, final_anchor_point)

        if red_circle_centers is not None:
            # TODO: Check if some of those need to be dropped
            resulting_mapping |= self.map_red_circles_to_key_points(
                *red_circle_centers,
                center_point=final_anchor_point
            )

        if blue_lines is not None:
            # TODO: Check if some of those need to be dropped
            resulting_mapping |= self.map_blue_lines_to_key_points(
                *blue_lines,
                center_point=final_anchor_point
            )

        if goal_zones_centers is not None:
            resulting_mapping |= self.map_goal_zones_to_key_points(
                *goal_zones_centers,
                center_point=final_anchor_point
            )

        if goal_lines is not None:
            resulting_mapping |= self.map_goal_lines(
                *goal_lines,
                center_point=final_anchor_point
            )

        return resulting_mapping

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
        :return: Новый словарь, дополненный соотнесенными точек.
        """

        # Перечисление пар для ключевых точек
        unused_line_points_mapping = {
            self.minimap_key_points.left_goal_line_top:
                self.minimap_key_points.left_goal_line_bottom,
            self.minimap_key_points.left_goal_line_after_zone_top:
                self.minimap_key_points.left_goal_line_after_zone_bottom,
            self.minimap_key_points.left_goal_line_after_zone_bottom:
                self.minimap_key_points.left_goal_line_after_zone_top,
            self.minimap_key_points.right_goal_line_top:
                self.minimap_key_points.right_goal_line_bottom,
            self.minimap_key_points.right_goal_line_after_zone_top:
                self.minimap_key_points.right_goal_line_after_zone_bottom,
            self.minimap_key_points.right_goal_line_after_zone_bottom:
                self.minimap_key_points.right_goal_line_after_zone_top
        }
        mapped_new_points: dict[KeyPoint, Point] = mapped_points.copy()

        # Map unused line points
        for line in goal_lines:
            # Get all lines point into used and unused point
            used_point: Point
            unused_point: Point

            if line.min_point not in mapped_new_points.values():
                used_point = line.max_point
                unused_point = line.min_point

                # Find point that was used to figure out it's key point
                for key_point, point in mapped_new_points.items():
                    if point == used_point:
                        # Assign complementary key point to the key point of a used point
                        new_key_point = unused_line_points_mapping[key_point]
                        mapped_new_points[new_key_point] = unused_point
                        break

            if line.max_point not in mapped_new_points.values():
                used_point = line.min_point
                unused_point = line.max_point

                for key_point, point in mapped_new_points.items():
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
        Соединяет две линии по расстоянию от точек.

        :param lines: Линии для объединения.
        :param from_point: Относительно какой точки объединять линии.
        :return: Комбинированная линия.
        """
        reverse_quadrant_lookup: dict[Point, PointQuadrant] = {}

        for line in lines:
            reverse_quadrant_lookup[line[0].min_point] = line[1]
            reverse_quadrant_lookup[line[0].max_point] = line[2]

        lines_data: list[Line] = [line for line, _, _ in lines]
        min_points: list[Point] = [line.min_point for line, _, _ in lines]
        max_points: list[Point] = [line.max_point for line, _, _ in lines]

        points: list[Point] = min_points + max_points
        points_distances: list[tuple[Point, Point, float]] = []

        for (p1, p2) in itertools.combinations(points, 2):
            if p1 == p2 or Line(p1, p2) in lines_data or Line(p2, p1) in lines_data:
                continue

            points_distances.append((p1, p2, p1.find_distance_from_point(p2)))

        points_distances.sort(key=lambda point_distance: point_distance[2])

        # Find one with highes distance from each other
        p1, p2, distance = max(points_distances, key=lambda pd: pd[2])

        if reverse_quadrant_lookup[p1][0] == HorizontalPosition.top:
            return Line(p1, p2)

        else:
            return Line(p2, p1)
