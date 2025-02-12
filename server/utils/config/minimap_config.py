from pydantic import BaseModel


class MinimapConfig(BaseModel):
    # Верхняя левая точка игрового поля
    top_left_corner_x: int
    top_left_corner_y: int

    # Нижняя правая точка игрового поля
    bottom_right_corner_x: int
    bottom_right_corner_y: int

    # Центр левой зоны ворот
    left_goal_zone_position_x: int
    left_goal_zone_position_y: int

    # Центр правой зоны ворот
    right_goal_zone_position_x: int
    right_goal_zone_position_y: int

    # Центральная линия
    red_line_top_position_x: int
    red_line_top_position_y: int

    red_line_bottom_position_x: int
    red_line_bottom_position_y: int

    # Синяя линия слева
    left_blue_line_top_position_x: int
    left_blue_line_top_position_y: int

    left_red_line_bottom_position_x: int
    left_red_line_bottom_position_y: int

    # Синяя линия справа
    right_blue_line_top_position_x: int
    right_blue_line_top_position_y: int

    right_red_line_bottom_position_x: int
    right_red_line_bottom_position_y: int

    # Синяя линия ворот слева
    left_goal_line_top_position_x: int
    left_goal_line_top_position_y: int

    left_goal_line_bottom_position_x: int
    left_goal_line_bottom_position_y: int

    # Синяя линия ворот справа
    right_goal_line_top_position_x: int
    right_goal_line_top_position_y: int

    right_goal_line_bottom_position_x: int
    right_goal_line_bottom_position_y: int
