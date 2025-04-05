from server.algorithms.data_types import BoundingBox, Point


def test_scaling_bounding_box():
    bbox = BoundingBox(
        Point(0, 0),
        Point(100, 100)
    )

    new_bbox = bbox.scale_bbox(0.5)
    assert new_bbox == BoundingBox(
        Point(25, 25),
        Point(75, 75)
    )
