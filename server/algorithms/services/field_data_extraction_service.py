from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from detectron2.structures import Instances

from server.algorithms.data_types.field_data import FieldData
from server.algorithms.data_types.field_extracted_data import FieldExtractedData
from server.algorithms.services.base.field_data_extraction_protocol import FieldDataExtractionProtocol

from server.algorithms.data_types import BoundingBox, Line, Point
from server.algorithms.key_point_placer import KeyPointPlacer


class FieldDataExtractionService(FieldDataExtractionProtocol):
    """
    Реализация сервиса получения данных о выделениях ключевых точек на поле.
    """
    def __init__(self, key_point_placer: KeyPointPlacer):
        self.key_point_placer: KeyPointPlacer = key_point_placer

    def get_field_data(
        self,
        detectron2_output: Instances,
        anchor_center_point: Optional[Point] = None
    ) -> FieldExtractedData:
        """
        Преобразует вывод Detectron2 в соотнесение точек с точками мини-карты.

        :param detectron2_output: Вывод нейросети.
        :param anchor_center_point: Пользовательская ключевая точка.
        :return: Информация о соотнесении точек и маске игрового поля на видео.
        """
        field_data: FieldData = FieldData.construct_field_data_from_output(
            detectron2_output
        )

        # Parameters for key mapping
        field_bbox: Optional[BoundingBox] = None
        blue_circle_center: Optional[Point] = None
        center_line: Optional[Line] = None
        red_circle_centers: Optional[tuple[Point, ...]] = None
        blue_lines_param: Optional[tuple[Line, ...]] = None
        goal_zones_centers: Optional[tuple[Point, ...]] = None
        goal_lines_param: Optional[tuple[Line, ...]] = None

        if field_data.field is None:
            raise ValueError("Must have at least field to process data")

        else:
            field_bbox = field_data.field.bbox

        if field_data.blue_circle:
            blue_circle_center = field_data.blue_circle.center_point

        if field_data.red_center_line:
            center_line = Line.find_lines(field_data.red_center_line.polygon.mask).clip_line_to_bounding_box(
                field_data.red_center_line.bbox
            )

        if field_data.red_circles:
            red_circle_centers = tuple([
                red_circle.center_point for red_circle in field_data.red_circles
            ])

            if len(red_circle_centers) == 0:
                red_circle_centers = None

        if field_data.blue_lines:
            blue_lines_param = tuple(filter(None, [
                Line.find_lines(blue_line.polygon.mask).clip_line_to_bounding_box(
                    blue_line.bbox
                ) for blue_line in field_data.blue_lines
            ]))

            if len(blue_lines_param) == 0:
                blue_lines_param = None

        if field_data.goal_zones:
            goal_zones_centers = tuple((goal_zone.center_point for goal_zone in field_data.goal_zones))

        if field_data.goal_lines:
            goal_lines_param = tuple(filter(None, [
                Line.find_lines(goal_line.polygon.mask) for goal_line in field_data.goal_lines
            ]))

            if len(goal_lines_param) == 0:
                goal_lines_param = None

        return FieldExtractedData(
            self.key_point_placer.map_to_key_points(
                field_bbox,
                anchor_center_point,
                blue_circle_center,
                center_line,
                red_circle_centers,
                blue_lines_param,
                goal_zones_centers,
                goal_lines_param
            ),
            field_data.field.polygon
        )
