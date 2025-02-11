from typing import TypedDict

import torch


class Detectron2Input(TypedDict):
    """
    Описывает входные данные для обработки с помощью Detectron2.
    """
    image: torch.Tensor
    height: int
    width: int
