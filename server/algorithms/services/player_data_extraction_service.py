# TODO: Implement service for fetching data from video about player movement
from typing import Optional, TYPE_CHECKING

import numpy
import torch
from detectron2.structures import Instances
from functorch.dim import Tensor

from server.algorithms.data_types.player_data import PlayerData
from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.nn import TeamDetectionPredictor
from server.algorithms.player_tracker import PlayerTracker
from server.algorithms.players_mapper import PlayersMapper

if TYPE_CHECKING:
    from server.algorithms.data_types import Mask, RawPlayerTrackingData, Point


class PlayerDataExtractionService:
    """
    Класс для обработки кадров видео и выделения информации об игроках.
    """
    def __init__(
        self,
        team_predictor: TeamDetectionPredictor,
        players_mapper: PlayersMapper,
        player_tracker: PlayerTracker,
        field_mask: Mask
    ):
        self.team_predictor: TeamDetectionPredictor = team_predictor
        self.players_mapped: PlayersMapper = players_mapper
        self.player_tracker: PlayerTracker = player_tracker
        self.field_mask: numpy.ndarray = field_mask.mask

    def process_frame(self, frame: numpy.ndarray, instances: Instances) -> list[PlayerData]:
        """
        Обрабатывает переданный кадр.

        :param frame: Кадр с игроками.
        :param instances: Выводы из Detectron2 с определениями классов игроков.
        :return: Список выделенных на кадре игроков и их номеров отслеживания.
        """
        output: list[PlayerData] = []

        # Filter out not on field
        threshold = 0.5
        filtered_instances: Instances = instances[instances.scores > threshold].to("cpu")

        # Find boxes
        boxes = filtered_instances.pred_boxes.tensor
        x_centers = (boxes[:, 0] + boxes[:, 2]) / 2  # Midpoint of x_min and x_max
        y_bottoms = boxes[:, 3]  # y_max (bottom coordinate)
        centers_bottoms: list[list[float]] = torch.stack((x_centers, y_bottoms), dim=1).to("cpu").tolist()

        # Keep on field
        keep = [self.field_mask[int(y) - 1, int(x) - 1] > 0 for x, y in centers_bottoms]
        keep_tensor = torch.tensor(keep, dtype=torch.bool)
        filtered_on_field = filtered_instances[keep_tensor]

        # Get required parameters
        boxes = filtered_on_field.pred_boxes.tensor
        scores: Tensor = filtered_on_field.scores
        classes_predicted: Tensor = filtered_on_field.pred_classes

        # Update tracking algorithm
        tracking_data: list[RawPlayerTrackingData] = self.player_tracker.update(
            boxes, scores, classes_predicted
        )

        # Filter out players
        player_indexes: list[int] = [
            n for n, track_data in enumerate(tracking_data)
                if track_data.player_class != PlayerClasses.Referee
        ]

        # Find out teams of players according to AI model
        # TODO: filter out those who are close to borders of image
        teams: dict[int, Team] = {
            player_index: self.team_predictor(
                tracking_data[player_index].bounding_box.cut_out_image_part(frame)
            )
            for player_index in player_indexes
        }

        # Find positions of players on mini map
        height, width, channels = frame.shape
        resolution: tuple[int, int] = (height, width)
        players_bottom_points: list[Point] = [
            tracked_player.bounding_box.bottom_point for tracked_player in tracking_data
        ]
        map_points: list[Point] = self.players_mapped.transform_point_to_minimap_coordinates(
            *players_bottom_points
        )

        for n, (player_data, map_point) in enumerate(zip(tracking_data, map_points)):
            player_team: Optional[Team] = teams.get(n)
            output.append(
                PlayerData(
                    player_data.tracking_id,
                    None,
                    map_point.to_relative_coordinates(resolution),
                    # TODO: Swap out for relative coordinates inside of bounding box for minimap
                    player_data.bounding_box.to_relative_coordinates(resolution),
                    player_data.player_class,
                    player_team
                )
            )

        # TODO: Finish implementation
        return output
