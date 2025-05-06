from enum import auto

from server.algorithms.enums.openapi_int_enum import OpenAPIIntEnum


class HorizontalPosition(OpenAPIIntEnum):
    top = auto()
    bottom = auto()
    center = auto()


class VerticalPosition(OpenAPIIntEnum):
    left = auto()
    right = auto()
    center = auto()
