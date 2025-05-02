from __future__ import annotations

from typing import TYPE_CHECKING

import torch
from detectron2.structures import Instances

from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.player_tracker import PlayerTracker
from server.data_storage.dto import BoxDTO, PointDTO, SubsetDataDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO

if TYPE_CHECKING:
    from torch import Tensor
    from server.algorithms.data_types import BoundingBox, CV_Image, Mask, RawPlayerTrackingData, Point


class PlayerTrackingService:
    """
    Класс для обработки кадров для получения игроков на видео с отслеживанием идентичности.
    """
    def __init__(
        self,
        player_tracker: PlayerTracker,
        field_mask: Mask,
        field_bounding_box: BoundingBox
    ):
        self.player_tracker: PlayerTracker = player_tracker
        self.field_mask: CV_Image = field_mask.mask
        self.field_bbox: BoundingBox = field_bounding_box.scale_bbox(0.8)

    def process_frame(
        self,
        frame_id: int,
        subset_id: int,
        instances: Instances
    ) -> list[SubsetDataDTO]:
        """
        Отслеживает идентичность игроков в кадрах.

        :param frame_id: Номер кадра, из которого получаются данные.
        :param subset_id: Номер поднабора данных.
        :param instances: Выводы из Detectron2 с определениями классов игроков.
        :return: Список выделенных на кадре игроков и их номеров отслеживания.
        """
        # Filter out not on field
        threshold = 0.5
        filtered_instances: Instances = instances[instances.scores > threshold].to("cpu")

        # Find boxes
        boxes = filtered_instances.pred_boxes.tensor
        x_centers = (boxes[:, 0] + boxes[:, 2]) / 2  # Midpoint of x_min and x_max
        y_bottoms = boxes[:, 3]  # y_max (bottom coordinate)
        centers_bottoms: list[list[float]] = torch.stack((x_centers, y_bottoms), dim=1).to("cpu").tolist()

        # Keep on field
        keep = [
            (self.field_mask[int(y) - 1, int(x) - 1] > 0) and ((x, y) in self.field_bbox)
            for x, y in centers_bottoms
        ]
        keep_tensor = torch.BoolTensor(keep)
        filtered_on_field = filtered_instances[keep_tensor]

        # Get required parameters
        boxes = filtered_on_field.pred_boxes.tensor
        scores: Tensor = filtered_on_field.scores
        classes_predicted: Tensor = filtered_on_field.pred_classes

        # Update tracking algorithm
        tracking_data: list[RawPlayerTrackingData] = self.player_tracker.update(
            boxes, scores, classes_predicted
        )

        output: list[SubsetDataDTO] = []
        for player_data in tracking_data:
            min_point: Point = player_data.bounding_box.min_point
            max_point: Point = player_data.bounding_box.max_point

            output.append(
                SubsetDataDTO(
                    tracking_id=player_data.tracking_id,
                    subset_id=subset_id,
                    frame_id=frame_id,
                    class_id=player_data.player_class,
                    team_id=None,
                    box=BoxDTO(
                        top_point=RelativePointDTO(x=min_point.x, y=min_point.y),
                        bottom_point=RelativePointDTO(x=max_point.x, y=max_point.y),
                    )
                )
            )

        return output

    @staticmethod
    def get_players_data_from_frame(
        frame: CV_Image,
        frame_data: list[SubsetDataDTO]
    ) -> list[tuple[Team, CV_Image]]:
        """
        Получает изображения игроков с назначенными командами.

        :param frame: Кадр с видео.
        :param frame_data: Информация об игроках на кадре.
        :return: Список назначенных команд и картинок игроков.
        """

        team_data: list[tuple[Team, CV_Image]] = []
        for player_data in frame_data:
            if player_data.class_id == PlayerClasses.Referee:
                continue

            if (player_team := player_data.team_id) is not None:
                player_with_team: SubsetDataDTO = player_data
                min_point: PointDTO = player_with_team.box.top_point
                max_point: PointDTO = player_with_team.box.bottom_point

                player_frame: CV_Image = BoundingBox(
                    min_point=Point(x=min_point.x, y=min_point.y),
                    max_point=Point(x=max_point.x, y=max_point.y)
                ).cut_out_image_part(frame)
                team_data.append((player_team, player_frame))

        return team_data
