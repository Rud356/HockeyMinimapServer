from dataclasses import dataclass
from typing import Optional

import numpy
from detectron2.structures import Instances

from server.algorithms.data_types.bounding_box import BoundingBox
from server.algorithms.data_types.field_instance import FieldInstance
from server.algorithms.data_types.mask import Mask
from server.algorithms.data_types.point import Point
from server.algorithms.enums.field_classes_enum import FieldClasses


@dataclass(repr=True)
class FieldData:
    """
    Описывает значения, выделенные с изображения поля нейросетью Detectron2.
    """
    field: Optional[FieldInstance] = None
    blue_circle: Optional[FieldInstance] = None
    red_circles: Optional[list[FieldInstance]] = None
    red_center_line: Optional[FieldInstance] = None
    blue_lines: Optional[list[FieldInstance]] = None
    goal_lines: Optional[list[FieldInstance]] = None
    goal_zones: Optional[list[FieldInstance]] = None

    @classmethod
    def construct_field_data_from_output(
        cls, detectron2_output: Instances
    ) -> "FieldData":
        """
        Подготавливает информацию о ключевых точках на основе выходных данных нейросети Detectron2.

        :param detectron2_output: Выходные данные нейросети.
        :return: Структурированные данные о поле.
        """
        output = cls()
        masks = detectron2_output.pred_masks.numpy()
        boxes = detectron2_output.pred_boxes
        boxes_centers: list[list[float]] = boxes.get_centers().tolist()
        classes_predicted: list[FieldClasses] = [
            FieldClasses(classifier) for classifier in detectron2_output.pred_classes.tolist()
        ]

        for mask, center, box, classified_as in zip(masks, boxes_centers, boxes, classes_predicted):
            instance_data: FieldInstance = FieldInstance(
                BoundingBox.calculate_combined_bbox(box),
                Mask((mask * 255).astype(numpy.uint8)),
                Point(center[0], center[1]),
                classified_as
            )

            match classified_as:
                case FieldClasses.Field:
                    # Field is only one object
                    if output.field is None:
                        output.field = instance_data

                    else:
                        new_bbox: BoundingBox = output.field.bbox.calculate_combined_bbox(box)
                        new_center: Point = new_bbox.center_point
                        output.field = FieldInstance(
                            new_bbox,
                            Mask.from_multiple_masks(
                                instance_data.polygon.mask,
                                output.field.polygon.mask
                            ),
                            new_center,
                            classified_as
                        )

                case FieldClasses.RedCircle:
                    # Multiple circles
                    if output.red_circles is None:
                        output.red_circles = [instance_data]

                    else:
                        output.red_circles.append(instance_data)

                case FieldClasses.BlueCircle:
                    # Can have only one
                    if output.blue_circle is None:
                        output.blue_circle = instance_data

                    else:
                        new_bbox = output.blue_circle.bbox.calculate_combined_bbox(box)
                        new_center = new_bbox.center_point
                        output.blue_circle = FieldInstance(
                            new_bbox,
                            Mask.from_multiple_masks(
                                instance_data.polygon.mask,
                                output.blue_circle.polygon.mask
                            ),
                            new_center,
                            classified_as
                        )

                case FieldClasses.RedCenterLine:
                    # Can have only one
                    if output.red_center_line is None:
                        output.red_center_line = instance_data

                    else:
                        new_bbox = output.red_center_line.bbox.calculate_combined_bbox(box)
                        new_center = new_bbox.center_point
                        output.red_center_line = FieldInstance(
                            new_bbox,
                            Mask.from_multiple_masks(
                                instance_data.polygon.mask,
                                output.red_center_line.polygon.mask
                            ),
                            new_center,
                            classified_as
                        )

                case FieldClasses.BlueLine:
                    # Multiple lines
                    if output.blue_lines is None:
                        output.blue_lines = [instance_data]

                    else:
                        output.blue_lines.append(instance_data)

                case FieldClasses.GoalZone:
                    # Multiple zones
                    if output.goal_zones is None:
                        output.goal_zones = [instance_data]

                    # Intersects with other goal zone, need union of those
                    elif output.goal_zones and any(
                        map(lambda v: instance_data.bbox.intersects_with(v.bbox), output.goal_zones)
                    ):
                        matching_zone: list[tuple[int, FieldInstance]] = [
                            (n, goal_zone) for n, goal_zone in enumerate(output.goal_zones)
                                if goal_zone.bbox.intersects_with(instance_data.bbox)
                        ]

                        if len(matching_zone) == 1:
                            matched_zone: tuple[int, FieldInstance] = matching_zone[0]
                            zone: FieldInstance = matched_zone[1]
                            new_bbox = zone.bbox.calculate_combined_bbox(box)
                            new_center = new_bbox.center_point
                            instance_data = FieldInstance(
                                new_bbox,
                                Mask.from_multiple_masks(
                                    instance_data.polygon.mask,
                                    zone.polygon.mask
                                ),
                                new_center,
                                classified_as
                            )

                            output.goal_zones[matched_zone[0]] = instance_data

                    else:
                        output.goal_zones.append(instance_data)

                case FieldClasses.GoalLine:
                    # Multiple lines
                    if output.goal_lines is None:
                        output.goal_lines = [instance_data]

                    else:
                        output.goal_lines.append(instance_data)

                case _:
                    # Ignore this case
                    pass

        # Expand mask to fix inconsistencies
        assert output.field is not None, "Field must be not None there"
        output.field.polygon = output.field.polygon.expand_mask()
        return output
