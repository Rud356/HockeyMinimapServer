import asyncio
from asyncio import Future, Queue
from pathlib import Path
from typing import ClassVar, Optional

import numpy
from detectron2 import model_zoo
from detectron2.config import get_cfg

from server.algorithms.batch_predictor import BatchPredictor
from server.algorithms.predictor_service import PredictorService


class PlayerPredictorService(PredictorService):
    """
    Класс сервиса обработки разметки игроков в фоновом режиме с помощью detectron2.
    """

    _model_zoo_path: ClassVar[str] = "COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"
    predictor: BatchPredictor
    device_lock: asyncio.Lock
    image_queue: Queue[tuple[tuple[numpy.ndarray, ...], Future]]

    def __init__(
        self,
        weights: Path,
        device: str,
        image_queue: Queue[tuple[tuple[numpy.ndarray, ...], Future]],
        threshold: float = 0.5,
        device_lock: Optional[asyncio.Lock] = None
    ):
        """
        Инициализирует сервис обработки нейронной сетью изображений поля с игроками для получения их типов и позиций.

        :param weights: Путь до весов модели.
        :param device: Имя устройства выполнения.
        :param threshold: Пороговое значение уверенности в верном результате для выделения.
        :param device_lock: Блокировщик доступа к устройству для избежания совместного использования
        при запуске нейросети.
        """
        cfg = get_cfg()
        cfg.merge_from_file(model_zoo.get_config_file(self._model_zoo_path))
        cfg.MODEL.WEIGHTS = str(weights.resolve())
        cfg.MODEL.ROI_HEADS.NUM_CLASSES = 3
        cfg.MODEL.DEVICE = device
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = threshold

        self.predictor = BatchPredictor(cfg)
        self.image_queue = image_queue
        self.device_lock = device_lock

        if self.device_lock is None:
            self.device_lock = asyncio.Lock()
