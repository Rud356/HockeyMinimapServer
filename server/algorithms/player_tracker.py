from typing import Any

import numpy as np
from deep_sort_realtime.deep_sort.track import Track
from deep_sort_realtime.deepsort_tracker import DeepSort
from torch import Tensor

from server.algorithms.data_types import BoundingBox
from server.algorithms.data_types.raw_player_tracking_data import RawPlayerTrackingData
from server.algorithms.enums.player_classes_enum import PlayerClasses

# TODO: try out this one https://github.com/levan92/deep_sort_realtime for finding players
class PlayerTracker:
    """
    Отслеживает идентичность игроков на поле между кадрами.
    """

    def __init__(self, start_from_id: int = 0, max_age=8, iou_threshold: float = 0.5):
        self.start_from_id: int = start_from_id
        self.tracker: DeepSort = DeepSort(
            max_iou_distance=iou_threshold,
            max_age=max_age,
            n_init=3,
            nms_max_overlap=0.5,
            gating_only_position=True
        )

    def update(self, boxes: Tensor, scores: Tensor, classes_predicted: Tensor, frame: np.ndarray) -> list[RawPlayerTrackingData]:
        """
        Обновляет отслеживания игроков на новый кадр.

        :param frame: Изображения с отслеживаемыми игроками.
        :param boxes: Охватывающие прямоугольники игроков.
        :param scores: Оценка уверенности в выделении.
        :param classes_predicted: Предсказанный класс игрока.
        :return: Список выделений игроков с их идентификаторами между кадрами.
        """
        dest: list = [
            (box.tolist(), score.item(), class_predicted.item())
                for box, score, class_predicted in zip(boxes, scores, classes_predicted)
            ]

        targets: list[Track] = self.tracker.update_tracks(dest, frame=frame)
        data: list[RawPlayerTrackingData] = []

        for target in targets:
            if not target.is_confirmed():
                continue

            data.append(
                RawPlayerTrackingData(
                    int(target.track_id) + self.start_from_id,
                    BoundingBox.calculate_combined_bbox(target.to_ltrb(orig=True).tolist()),
                    PlayerClasses(target.det_class),
                )
            )

        return data
