import asyncio
from asyncio import Future, Queue
from pathlib import Path
from typing import ClassVar, Optional

from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.structures import Instances

from server.algorithms.data_types import CV_Image
from server.algorithms.nn.batch_predictor import BatchPredictor
from server.algorithms.services.base.predictor_service import PredictorService


class FieldPredictorService(PredictorService):
    """
    Класс сервиса обработки разметки поля в фоновом режиме с помощью detectron2.
    """
    _model_zoo_path: ClassVar[str] = "COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"

    def __init__(
        self,
        weights: Path,
        device: str,
        image_queue: Queue[
            tuple[
                tuple[CV_Image, ...],
                Future[list[Instances]]
            ]
        ],
        threshold: float = 0.5,
        device_lock: Optional[asyncio.Lock] = None
    ):
        """
        Инициализирует сервис обработки нейронной сетью изображений поля для получения разметки.

        :param weights: Путь до весов модели.
        :param device: Имя устройства выполнения.
        :param threshold: Пороговое значение уверенности в верном результате для выделения.
        :param device_lock: Блокировщик доступа к устройству для избежания совместного использования
            при запуске нейросети.
        """
        cfg = get_cfg()
        cfg.merge_from_file(model_zoo.get_config_file(self._model_zoo_path))
        cfg.MODEL.WEIGHTS = str(weights.resolve())
        cfg.MODEL.ROI_HEADS.NUM_CLASSES = 8
        cfg.MODEL.DEVICE = device
        cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = threshold
        cfg.INPUT.MIN_SIZE_TEST = 700
        cfg.INPUT.MAX_SIZE_TEST = 700

        self.predictor = BatchPredictor(cfg)
        self.image_queue = image_queue


        if device_lock is None:
            self.device_lock = asyncio.Lock()

        else:
            self.device_lock = device_lock
