from pydantic import BaseModel
from server.utils.config.key_point import KeyPoint


class MinimapKeyPointConfig(BaseModel):
    # Границы абсолютных координат поля мини-карты
    top_left_field_point: KeyPoint
    bottom_right_field_point: KeyPoint

    # Левая зона гола
    left_goal_zone: KeyPoint
    # Правая зона гола
    right_goal_zone: KeyPoint

    # Центральная линия
    center_line_top: KeyPoint
    center_line_bottom: KeyPoint

    # Левая синяя линия
    left_blue_line_top: KeyPoint
    left_blue_line_bottom: KeyPoint

    # Правая синяя линия
    right_blue_line_top: KeyPoint
    right_blue_line_bottom: KeyPoint

    # Левая линия гола
    left_goal_line_top: KeyPoint
    left_goal_line_bottom: KeyPoint
    left_goal_line_after_zone_top: KeyPoint
    left_goal_line_after_zone_bottom: KeyPoint

    # Левая линия гола
    right_goal_line_top: KeyPoint
    right_goal_line_bottom: KeyPoint
    right_goal_line_after_zone_top: KeyPoint
    right_goal_line_after_zone_bottom: KeyPoint

    # Синие круги
    blue_circle_top_left: KeyPoint
    blue_circle_top_right: KeyPoint
    blue_circle_bottom_left: KeyPoint
    blue_circle_bottom_right: KeyPoint

