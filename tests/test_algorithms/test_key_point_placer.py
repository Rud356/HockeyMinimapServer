import pytest

from server.algorithms.data_types import Line, Point
from server.algorithms.enums.camera_position import CameraPosition
from server.algorithms.enums.coordinate_split import HorizontalPosition, VerticalPosition
from server.utils.config import MinimapKeyPointConfig
from server.algorithms.key_point_placer import KeyPointPlacer


@pytest.fixture()
def key_points() -> MinimapKeyPointConfig:
    return MinimapKeyPointConfig(**
        {
            "top_left_field_point": {"x": 16, "y": 88},
            "bottom_right_field_point": {"x": 1247, "y": 704},

            "left_goal_zone": {"x": 116, "y": 396},
            "right_goal_zone": {"x": 1144, "y": 396},

            "center_line_top": {"x": 630, "y": 92},
            "center_line_bottom": {"x": 630, "y": 700},

            "left_blue_line_top": {"x": 423, "y": 92},
            "left_blue_line_bottom": {"x": 423, "y": 700},

            "right_blue_line_top": {"x": 838, "y": 92},
            "right_blue_line_bottom": {"x": 838, "y": 700},

            "left_goal_line_top": {"x": 99, "y": 105},
            "left_goal_line_bottom": {"x": 99, "y": 360},

            "left_goal_line_after_zone_top": {"x": 99, "y": 433},
            "left_goal_line_after_zone_bottom": {"x": 99, "y": 688},

            "right_goal_line_top": {"x": 1162, "y": 105},
            "right_goal_line_bottom": {"x": 1162, "y": 360},

            "right_goal_line_after_zone_top": {"x": 1162, "y": 433},
            "right_goal_line_after_zone_bottom": {"x": 1162, "y": 688},

            "center_circle": {"x": 630, "y": 396},
            "red_circle_top_left": {"x": 241, "y": 243},
            "red_circle_top_right": {"x": 1020, "y": 243},
            "red_circle_bottom_left": {"x": 241, "y": 550},
            "red_circle_bottom_right": {"x": 1020, "y": 550}
        }
    )


def key_points_placer_factory(key_points: MinimapKeyPointConfig, cam_pos: CameraPosition, resolution=(1280, 720)) -> KeyPointPlacer:
    return KeyPointPlacer(
        key_points, cam_pos, resolution
    )


def test_flip_quadrants_horizontally():
    new_quadrants = KeyPointPlacer.flip_quadrant_horizontally(
        (HorizontalPosition.top, VerticalPosition.left),
        (HorizontalPosition.top, VerticalPosition.right),
        (HorizontalPosition.top, VerticalPosition.center),
        (HorizontalPosition.bottom, VerticalPosition.left),
        (HorizontalPosition.bottom, VerticalPosition.right),
        (HorizontalPosition.bottom, VerticalPosition.center),
        (HorizontalPosition.center, VerticalPosition.center),
    )

    assert new_quadrants == [
        (HorizontalPosition.bottom, VerticalPosition.left),
        (HorizontalPosition.bottom, VerticalPosition.right),
        (HorizontalPosition.bottom, VerticalPosition.center),
        (HorizontalPosition.top, VerticalPosition.left),
        (HorizontalPosition.top, VerticalPosition.right),
        (HorizontalPosition.top, VerticalPosition.center),
        (HorizontalPosition.center, VerticalPosition.center),
    ], "Invalid quadrants flip"


def test_flip_quadrants_vertically():
    new_quadrants = KeyPointPlacer.flip_quadrant_vertically(
        (HorizontalPosition.top, VerticalPosition.left),
        (HorizontalPosition.top, VerticalPosition.right),
        (HorizontalPosition.top, VerticalPosition.center),
        (HorizontalPosition.bottom, VerticalPosition.left),
        (HorizontalPosition.bottom, VerticalPosition.right),
        (HorizontalPosition.bottom, VerticalPosition.center),
        (HorizontalPosition.center, VerticalPosition.center),
    )

    assert new_quadrants == [
        (HorizontalPosition.top, VerticalPosition.right),
        (HorizontalPosition.top, VerticalPosition.left),
        (HorizontalPosition.top, VerticalPosition.center),
        (HorizontalPosition.bottom, VerticalPosition.right),
        (HorizontalPosition.bottom, VerticalPosition.left),
        (HorizontalPosition.bottom, VerticalPosition.center),
        (HorizontalPosition.center, VerticalPosition.center),
    ], "Invalid quadrants flip"


def test_determining_quadrant():
    assert KeyPointPlacer.determine_quadrant(
        Point(0.8, 0.3),
        Point(0.5, 0.5)
    ) == (HorizontalPosition.top, VerticalPosition.right), "Invalid quadrant placement for top right"

    assert KeyPointPlacer.determine_quadrant(
        Point(1, 1), # Bottom right
        Point(0.5, 0.5) # Center
    ) == (HorizontalPosition.bottom, VerticalPosition.right), "Invalid quadrant placement for bottom right"

    assert KeyPointPlacer.determine_quadrant(
        Point(0.3, 0.1),
        Point(0.5, 0.5)
    ) == (HorizontalPosition.top, VerticalPosition.left), "Invalid quadrant placement for top left"

    assert KeyPointPlacer.determine_quadrant(
        Point(0.3, 1),
        Point(0.5, 0.5)
    ) == (HorizontalPosition.bottom, VerticalPosition.left), "Invalid quadrant placement for bottom left"


def test_blue_lines_key_points_on_position_1(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.top_left_corner)
    center_point = Point(976, 242)

    assert key_points_placer.map_blue_lines_to_key_points(
        Line(Point(1079, 70), Point(1275, 376)),
        Line(Point(739, 44), Point(746, 630)),
        center_point=center_point
    ) == {
        key_points.left_blue_line_top: Point(1275, 376),
        key_points.left_blue_line_bottom: Point(1079, 70),
        key_points.right_blue_line_top: Point(746, 630),
        key_points.right_blue_line_bottom: Point(739, 44)
    }


def test_blue_lines_key_points_on_position_4(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.bottom_left_corner)
    center_point = Point(976, 242)

    assert key_points_placer.map_blue_lines_to_key_points(
        Line(Point(1079, 70), Point(1275, 376)),
        Line(Point(739, 44), Point(746, 630)),
        center_point=center_point
    ) == {
        key_points.right_blue_line_bottom: Point(1275, 376),
        key_points.right_blue_line_top: Point(1079, 70),
        key_points.left_blue_line_bottom: Point(746, 630),
        key_points.left_blue_line_top: Point(739, 44)
    }


def test_blue_lines_key_point_on_position_7(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.left_side_camera)
    center_point = Point(992, 475)

    assert key_points_placer.map_blue_lines_to_key_points(
        Line(Point(684, 533), Point(1311, 582)),
        Line(Point(789, 427), Point(1230, 436)),
        center_point=center_point
    ) == {
        key_points.right_blue_line_bottom: Point(1230, 436),
        key_points.right_blue_line_top: Point(789, 427),
        key_points.left_blue_line_bottom: Point(1311, 582),
        key_points.left_blue_line_top: Point(684, 533)
    }


def test_red_circles_key_points_on_position_1(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.top_left_corner)
    center_point = Point(976, 242)

    assert key_points_placer.map_red_circles_to_key_points(
        Point(1079, 70), Point(1275, 376),
        Point(739, 44), Point(746, 630),
        center_point=center_point
    ) == {
        key_points.red_circle_top_left: Point(1275, 376),
        key_points.red_circle_bottom_left: Point(1079, 70),
        key_points.red_circle_top_right: Point(746, 630),
        key_points.red_circle_bottom_right: Point(739, 44)
    }


def test_red_circles_key_points_on_position_4(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.bottom_left_corner)
    center_point = Point(976, 242)

    result = key_points_placer.map_red_circles_to_key_points(
        Point(1079, 70), Point(1275, 376),
        Point(739, 44), Point(746, 630),
        center_point=center_point
    )

    assert result == {
        key_points.red_circle_bottom_right: Point(1275, 376),
        key_points.red_circle_top_right: Point(1079, 70),
        key_points.red_circle_bottom_left: Point(746, 630),
        key_points.red_circle_top_left: Point(739, 44)
    }


def test_red_circles_key_point_on_position_7(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.left_side_camera)
    center_point = Point(992, 475)

    assert key_points_placer.map_red_circles_to_key_points(
        Point(684, 533), Point(1311, 582),
        Point(789, 427), Point(1230, 436),
        center_point=center_point
    ) == {
        key_points.red_circle_bottom_right: Point(1230, 436),
        key_points.red_circle_top_right: Point(789, 427),
        key_points.red_circle_bottom_left: Point(1311, 582),
        key_points.red_circle_top_left: Point(684, 533)
    }


def test_goal_zones_to_key_points_on_position_1(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.top_left_corner)
    center_point = Point(976, 242)

    assert key_points_placer.map_goal_zones_to_key_points(
        Point(148, 194), center_point=center_point
    ) == {key_points.right_goal_zone: Point(148, 194)}

    assert key_points_placer.map_goal_zones_to_key_points(
        Point(148, 194), Point(1270, 640), center_point=center_point
    ) == {
        key_points.right_goal_zone: Point(148, 194),
        key_points.left_goal_zone: Point(1270, 640)
    }


def test_goal_zones_to_key_points_on_position_4(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.bottom_left_corner)
    center_point = Point(976, 242)

    assert key_points_placer.map_goal_zones_to_key_points(
        Point(148, 194), center_point=center_point
    ) == {key_points.left_goal_zone: Point(148, 194)}

    assert key_points_placer.map_goal_zones_to_key_points(
        Point(148, 194), Point(1270, 640), center_point=center_point
    ) == {
        key_points.left_goal_zone: Point(148, 194),
        key_points.right_goal_zone: Point(1270, 640)
    }


def test_goal_zones_key_point_on_position_7(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.left_side_camera)
    center_point = Point(992, 475)

    assert key_points_placer.map_goal_zones_to_key_points(
        Point(955, 738),
        Point(988, 389),
        center_point=center_point
    ) == {
        key_points.left_goal_zone: Point(955, 738),
        key_points.right_goal_zone: Point(988, 389),
    }


def test_goal_lines_key_points_on_position_7_4_lines(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.left_side_camera)
    center_point = Point(992, 475)

    top_left_line = Line(Point(463, 743), Point(860, 793))
    bottom_left_line = Line(Point(1020, 794), Point(1409, 836))
    top_right_line = Line(Point(850, 353), Point(986, 373))
    bottom_right_line = Line(Point(1039, 372), Point(1196, 367))

    example_result = {
        key_points.left_goal_line_top: top_left_line.min_point,
        key_points.left_goal_line_bottom: top_left_line.max_point,

        key_points.left_goal_line_after_zone_top: bottom_left_line.min_point,
        key_points.left_goal_line_after_zone_bottom: bottom_left_line.max_point,

        key_points.right_goal_line_top: top_right_line.min_point,
        key_points.right_goal_line_bottom: top_right_line.max_point,

        key_points.right_goal_line_after_zone_top: bottom_right_line.min_point,
        key_points.right_goal_line_after_zone_bottom: bottom_right_line.max_point
    }

    result = key_points_placer.map_goal_lines(
        top_left_line, top_right_line, bottom_right_line, bottom_left_line,
        center_point=center_point
    )

    assert result == example_result


def test_goal_lines_key_points_on_position_7_3_lines(key_points):
    key_points_placer = key_points_placer_factory(
        key_points, CameraPosition.left_side_camera,
        resolution=(1920, 1080)
    )
    center_point = Point(992, 475)

    top_left_line = Line(Point(463, 743), Point(860, 793))
    bottom_left_line = Line(Point(1020, 794), Point(1409, 836))
    top_right_line = Line(Point(850, 353), Point(986, 373))
    bottom_right_line = Line(Point(1039, 372), Point(1196, 367))

    example_result = {
        key_points.left_goal_line_top: top_left_line.min_point,
        key_points.left_goal_line_bottom: top_left_line.max_point,

        key_points.right_goal_line_top: top_right_line.min_point,
        key_points.right_goal_line_bottom: top_right_line.max_point,

        key_points.right_goal_line_after_zone_top: bottom_right_line.min_point,
        key_points.right_goal_line_after_zone_bottom: bottom_right_line.max_point
    }

    result = key_points_placer.map_goal_lines(
        top_left_line, top_right_line, bottom_right_line,
        center_point=center_point
    )

    assert result == example_result

    example_result = {
        key_points.left_goal_line_top: top_left_line.min_point,
        key_points.left_goal_line_bottom: top_left_line.max_point,

        key_points.left_goal_line_after_zone_top: bottom_left_line.min_point,
        key_points.left_goal_line_after_zone_bottom: bottom_left_line.max_point,

        key_points.right_goal_line_top: top_right_line.min_point,
        key_points.right_goal_line_bottom: top_right_line.max_point,
    }

    result = key_points_placer.map_goal_lines(
        top_left_line, top_right_line, bottom_left_line,
        center_point=center_point
    )

    assert result == example_result

    example_result = {
        key_points.left_goal_line_after_zone_top: bottom_left_line.min_point,
        key_points.left_goal_line_after_zone_bottom: bottom_left_line.max_point,

        key_points.right_goal_line_top: top_right_line.min_point,
        key_points.right_goal_line_bottom: top_right_line.max_point,

        key_points.right_goal_line_after_zone_top: bottom_right_line.min_point,
        key_points.right_goal_line_after_zone_bottom: bottom_right_line.max_point
    }

    result = key_points_placer.map_goal_lines(
        top_right_line, bottom_right_line, bottom_left_line,
        center_point=center_point
    )

    assert result == example_result


def test_goal_lines_key_points_on_position_7_2_lines(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.left_side_camera)
    center_point = Point(992, 475)

    top_right_line = Line(Point(850, 353), Point(986, 373))
    bottom_right_line = Line(Point(1039, 372), Point(1196, 367))

    example_result = {
        key_points.right_goal_line_top: top_right_line.min_point,
        key_points.right_goal_line_bottom: top_right_line.max_point,

        key_points.right_goal_line_after_zone_top: bottom_right_line.min_point,
        key_points.right_goal_line_after_zone_bottom: bottom_right_line.max_point
    }

    result = key_points_placer.map_goal_lines(
        top_right_line, bottom_right_line,
        center_point=center_point
    )

    assert result == example_result


def test_goal_lines_key_points_on_position_7_1_line(key_points):
    key_points_placer = key_points_placer_factory(key_points, CameraPosition.left_side_camera)
    center_point = Point(992, 475)

    top_left_line = Line(Point(463, 743), Point(860, 793))
    bottom_left_line = Line(Point(1020, 794), Point(1409, 836))
    top_right_line = Line(Point(850, 353), Point(986, 373))
    bottom_right_line = Line(Point(1039, 372), Point(1196, 367))

    example_result = {
        key_points.right_goal_line_after_zone_top: bottom_right_line.min_point,
        key_points.right_goal_line_after_zone_bottom: bottom_right_line.max_point
    }

    result = key_points_placer.map_goal_lines(
        bottom_right_line,
        center_point=center_point
    )

    assert result == example_result

    example_result = {
        key_points.right_goal_line_top: top_right_line.min_point,
        key_points.right_goal_line_bottom: top_right_line.max_point,
    }

    result = key_points_placer.map_goal_lines(
        top_right_line,
        center_point=center_point
    )

    assert result == example_result

    example_result = {
        key_points.left_goal_line_top: top_left_line.min_point,
        key_points.left_goal_line_bottom: top_left_line.max_point,
    }

    result = key_points_placer.map_goal_lines(
        top_left_line,
        center_point=center_point
    )

    assert result == example_result

    example_result = {
        key_points.left_goal_line_after_zone_top: bottom_left_line.min_point,
        key_points.left_goal_line_after_zone_bottom: bottom_left_line.max_point,
    }

    result = key_points_placer.map_goal_lines(
        bottom_left_line,
        center_point=center_point
    )

    assert result == example_result
