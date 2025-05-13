from pydantic import BaseModel, Field

from server.utils.config.key_point import KeyPoint


class MinimapKeyPointConfig(BaseModel):
    """
    Описывает положения ключевых точек на карте.
    """
    # Границы абсолютных координат поля мини-карты
    top_left_field_point: KeyPoint = Field(
        description="Верхний левый угол карты поля, "
                    "от которого строятся относительные координаты"
    )
    bottom_right_field_point: KeyPoint = Field(
        description="Правый нижний угол карты поля, "
                    "от которого строятся относительные координаты"
    )

    # Левая зона гола
    left_goal_zone: KeyPoint = Field(
        description="Левая зона гола"
    )
    # Правая зона гола
    right_goal_zone: KeyPoint = Field(
        description="Правая зона гола"
    )

    # Центральная линия
    center_line_top: KeyPoint = Field(
        description="Верхняя точка центральной линии"
    )
    center_line_bottom: KeyPoint = Field(
        description="Нижняя точка центральной линии"
    )

    # Левая синяя линия
    left_blue_line_top: KeyPoint = Field(
        description="Верхняя точка левой синей линии"
    )
    left_blue_line_bottom: KeyPoint = Field(
        description="Нижняя точка левой синей линии"
    )

    # Правая синяя линия
    right_blue_line_top: KeyPoint = Field(
        description="Верхняя точка правой синей линии"
    )
    right_blue_line_bottom: KeyPoint = Field(
        description="Нижняя точка правой синей линии"
    )

    # Левая линия гола
    left_goal_line_top: KeyPoint = Field(
        description="Верхняя точка верхней линии левой зоны гола"
    )
    left_goal_line_bottom: KeyPoint = Field(
        description="Нижняя точка верхней линии левой зоны гола"
    )
    left_goal_line_after_zone_top: KeyPoint = Field(
        description="Верхняя точка нижней линии, идущей после левой зоны гола"
    )
    left_goal_line_after_zone_bottom: KeyPoint = Field(
        description="Верхняя точка нижней линии, идущей после левой зоны гола"
    )

    # Правая линия гола
    right_goal_line_top: KeyPoint = Field(
        description="Верхняя точка верхней линии правой зоны гола"
    )
    right_goal_line_bottom: KeyPoint = Field(
        description="Нижняя точка верхней линии правой зоны гола"
    )
    right_goal_line_after_zone_top: KeyPoint = Field(
        description="Верхняя точка нижней линии, идущей после правой зоны гола"
    )
    right_goal_line_after_zone_bottom: KeyPoint = Field(
        description="Верхняя точка нижней линии, идущей после правой зоны гола"
    )

    # Красные круги
    red_circle_top_left: KeyPoint = Field(
        description="Красный круг слева сверху"
    )
    red_circle_top_right: KeyPoint = Field(
        description="Красный круг права сверху"
    )
    red_circle_bottom_left: KeyPoint  = Field(
        description="Красный круг справа сверху"
    )
    red_circle_bottom_right: KeyPoint = Field(
        description="Красный круг справа снизу"
    )

    # Центральный круг
    center_circle: KeyPoint = Field(
        description="Точка центрального круга"
    )
