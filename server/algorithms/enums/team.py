from enum import auto

from server.algorithms.enums.openapi_int_enum import OpenAPIIntEnum


class Team(OpenAPIIntEnum):
    Home = auto()
    Away = auto()
