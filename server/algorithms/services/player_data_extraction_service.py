# TODO: Implement service for fetching data from video about player movement
from __future__ import annotations

from typing import Optional, TYPE_CHECKING

import numpy
import torch
from detectron2.structures import Instances

from server.algorithms.data_types.player_data import PlayerData
from server.algorithms.enums import Team
from server.algorithms.enums.player_classes_enum import PlayerClasses
from server.algorithms.nn import TeamDetectionPredictor
from server.algorithms.player_tracker import PlayerTracker
from server.algorithms.players_mapper import PlayersMapper

if TYPE_CHECKING:
    from torch import Tensor
    from server.algorithms.data_types import BoundingBox, Mask, RawPlayerTrackingData, Point


class PlayerDataExtractionService:
    """
    Класс для обработки кадров видео и выделения информации об игроках.
    """
    __slots__ = (
        "team_predictor",
        "players_mapper",
        "player_tracker",
        "field_mask",
        "field_bbox",
        "known_tracked_players_teams"
    )

    def __init__(
        self,
        team_predictor: TeamDetectionPredictor,
        players_mapper: PlayersMapper,
        player_tracker: PlayerTracker,
        field_mask: Mask,
        field_bounding_box: BoundingBox
    ):
        self.team_predictor: TeamDetectionPredictor = team_predictor
        self.players_mapper: PlayersMapper = players_mapper
        self.player_tracker: PlayerTracker = player_tracker
        self.field_mask: numpy.ndarray = field_mask.mask
        self.field_bbox: BoundingBox = field_bounding_box
        self.known_tracked_players_teams: dict[int, Team] = {}

    def process_frame(
        self,
        frame: numpy.ndarray,
        instances: Instances,
    ) -> list[PlayerData]:
        """
        Обрабатывает переданный кадр.

        :param frame: Кадр с игроками.
        :param instances: Выводы из Detectron2 с определениями классов игроков.
        :return: Список выделенных на кадре игроков и их номеров отслеживания.
        """
        output: list[PlayerData] = []
        team_detection_bbox: BoundingBox = self.field_bbox.scale_bbox()

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

        # Filter out players who don't need team detection
        player_indexes_to_detect_team: list[int] = [
            n for n, track_data in enumerate(tracking_data)
                if (
                    track_data.player_class != PlayerClasses.Referee and
                    track_data.bounding_box.bottom_point in team_detection_bbox and
                    track_data.tracking_id not in self.known_tracked_players_teams
                )
        ]

        # Find out teams of players according to AI model
        teams: dict[int, Team] = {
            player_index: self.team_predictor(
                tracking_data[player_index].bounding_box.cut_out_image_part(frame)
            )
            for player_index in player_indexes_to_detect_team
        }

        # Find positions of players on mini map
        height, width, channels = frame.shape
        resolution: tuple[int, int] = (height, width)
        players_bottom_points: list[Point] = [
            tracked_player.bounding_box.bottom_point for tracked_player in tracking_data
        ]
        map_points: list[Point] = self.players_mapper.transform_point_to_minimap_coordinates(
            *players_bottom_points
        )

        for n, (player_data, map_point) in enumerate(zip(tracking_data, map_points)):
            # Choose source of team (detected now, or detected before)
            player_team: Optional[Team] = teams.get(n) or self.known_tracked_players_teams.get(player_data.tracking_id)

            if (player_team is not None) and (player_data.tracking_id not in self.known_tracked_players_teams):
                self.known_tracked_players_teams[player_data.tracking_id] = player_team

            output.append(
                PlayerData(
                    player_data.tracking_id,
                    None,
                    map_point.to_relative_coordinates_inside_bbox(self.players_mapper.map_bbox),
                    player_data.bounding_box.to_relative_coordinates(resolution),
                    player_data.player_class,
                    player_team
                )
            )

        return output
