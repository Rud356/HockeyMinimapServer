from typing import Any

import numpy as np
from sort.tracker import SortTracker
from torch import Tensor

from server.algorithms.data_types import BoundingBox
from server.algorithms.data_types.raw_player_tracking_data import RawPlayerTrackingData
from server.algorithms.enums.player_classes_enum import PlayerClasses


class PlayerTracker:
    """
    Отслеживает идентичность игроков на поле между кадрами.
    """

    def __init__(self, start_from_id: int = 0, track_length: int = 6, min_hits: int = 4, iou_threshold: float = 0.2):
        self.start_from_id: int = start_from_id
        self.tracker: SortTracker = SortTracker(track_length, min_hits, iou_threshold)

    def update(self, boxes: Tensor, scores: Tensor, classes_predicted: Tensor) -> list[RawPlayerTrackingData]:
        """
        Обновляет отслеживания игроков на новый кадр.

        :param boxes: Охватывающие прямоугольники игроков.
        :param scores: Оценка уверенности в выделении.
        :param classes_predicted: Предсказанный класс игрока.
        :return: Список выделений игроков с их идентификаторами между кадрами.
        """
        dest: np.ndarray = np.array(
            [
                np.array(
                    [*box, score, class_predicted]
                ) for box, score, class_predicted in zip(boxes, scores, classes_predicted)
            ]
        )

        targets: Any = self.tracker.update(dest).astype(np.int32).tolist()
        data: list[RawPlayerTrackingData] = []

        for target in targets:
            data.append(
                RawPlayerTrackingData(
                    int(target[4]) + self.start_from_id,
                    BoundingBox.calculate_combined_bbox(target[:4]),
                    PlayerClasses(int(target[5])),
                    float(target[6])
                )
            )

        return data
