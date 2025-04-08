from server.algorithms.data_types import BoundingBox, RelativePoint
from server.algorithms.data_types.point import Point


def test_convertion_from_bounding_box():
    bbox = BoundingBox(
        Point(0, 0),
        Point(100, 100)
    )

    point = Point(
        50, 50
    )

    assert point.to_relative_coordinates_inside_bbox(bbox) == RelativePoint(
        0.5, 0.5
    )


def test_convertion_from_bounding_box_with_no_empty_top():
    # Moved top point to 16 pixels down and to the right
    bbox = BoundingBox(
        Point(16, 16),
        Point(116, 116)
    )

    point = Point(
        66, 66
    )

    assert point.to_relative_coordinates_inside_bbox(bbox) == RelativePoint(
        0.5, 0.5
    )



def test_convertion_from_bounding_box_and_back():
    bbox = BoundingBox(
        Point(0, 0),
        Point(100, 100)
    )

    point = Point(
        50, 50
    )

    assert Point.from_relative_coordinates_inside_bbox(
        point.to_relative_coordinates_inside_bbox(bbox),
        bbox
    ) == point


def test_convertion_from_bounding_box_and_back_with_non_zero_top():
    bbox = BoundingBox(
        Point(16, 16),
        Point(116, 116)
    )

    point = Point(
        66, 66
    )

    assert Point.from_relative_coordinates_inside_bbox(
        point.to_relative_coordinates_inside_bbox(bbox),
        bbox
    ) == point


def test_convertion_from_bounding_box_and_back_with_uneven_top_point():
    bbox = BoundingBox(
        Point(36, 46),
        Point(100, 100)
    )

    point = Point(
        66, 66
    )

    assert Point.from_relative_coordinates_inside_bbox(
        point.to_relative_coordinates_inside_bbox(bbox),
        bbox
    ) == point


def test_convertion_from_bounding_box_and_back_with_uneven_points():
    bbox = BoundingBox(
        Point(36, 46),
        Point(97, 188)
    )

    point = Point(
        39, 61
    )

    assert Point.from_relative_coordinates_inside_bbox(
        point.to_relative_coordinates_inside_bbox(bbox),
        bbox
    ) == point
