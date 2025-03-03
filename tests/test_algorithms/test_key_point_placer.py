import pytest

from server.algorithms.data_types import Point
from server.algorithms.enums.coordinate_split import HorizontalPosition, VerticalPosition
from server.utils.config import MinimapKeyPointConfig
from server.algorithms.key_point_placer import KeyPointPlacer


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

