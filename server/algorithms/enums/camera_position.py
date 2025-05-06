from enum import auto

from server.algorithms.enums.openapi_int_enum import OpenAPIIntEnum


class CameraPosition(OpenAPIIntEnum):
    top_left_corner = auto()
    top_middle_point = auto()
    top_right_corner = auto()

    bottom_left_corner = auto()
    bottom_middle_point = auto()
    bottom_right_corner = auto()

    right_side_camera = auto()
    left_side_camera = auto()
