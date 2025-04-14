from __future__ import annotations

from typing import Literal, TYPE_CHECKING

import cv2
import torch
from PIL import Image

from server.algorithms.data_types import CV_Image
from server.algorithms.enums.team import Team
from server.algorithms.nn.team_detector_teacher import team_detector_transform

if TYPE_CHECKING:
    from torch import Tensor
    from server.algorithms.nn.team_detector import TeamDetectorModel


class TeamDetectionPredictor:
    def __init__(
        self,
        model: TeamDetectorModel,
        transform_inputs=team_detector_transform,
        device: Literal['cpu', 'cuda'] | str = 'cpu'
    ):
        """
        Инициализация класса для определения команды с помощью нейронной сети.

        :param model: Обученная модель машинного обучения.
        :param transform_inputs: Входные параметры преобразования входных данных.
        """
        self.device = device
        self.model = model.to(device)
        self.transform = transform_inputs

    def __call__(self, image: CV_Image) -> Team:
        """
        Выполняет определение команды игрока с помощью нейронной сети.

        :param image: Изображение в формате OpenCV.
        :return: Определение команды.
        """

        image_converted: Image.Image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        image_eval: Tensor = self.transform(image_converted).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(image_eval).to('cpu')
            _, predicted = torch.max(output, 1)

            if predicted.item() == Team.Home:
                return Team.Home

            elif predicted.item() == Team.Away:
                return Team.Away

            return Team.Away
