from enum import IntEnum, auto


class CameraPosition(IntEnum):
    top_left_corner = auto()
    top_middle_point = auto()
    top_right_corner = auto()

    bottom_left_corner = auto()
    bottom_middle_point = auto()
    bottom_right_corner = auto()
