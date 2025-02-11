import asyncio
import threading
from asyncio import Future, InvalidStateError, Queue
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import ClassVar, Optional

import numpy
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.structures import Instances

from server.algorithms.batch_predictor import BatchPredictor


class PlayerPredictorService:
    """
    Класс сервиса обработки разметки игроков в фоновом режиме с помощью detectron2.
    """

    _model_zoo_path: ClassVar[str] = "COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"
    predictor: BatchPredictor
    device_lock: threading.Lock
    image_queue: Queue[tuple[tuple[numpy.ndarray, ...], Future]]

    def __init__(
        self,
        weights: Path,
        device: str,
        image_queue: Queue[tuple[tuple[numpy.ndarray, ...], Future]],
        threshold: float = 0.5,
        device_lock: Optional[threading.Lock] = None
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
            self.device_lock = threading.Lock()

    async def __call__(self) -> None:
        """
        Обрабатывает изображения в режиме сервиса на устройстве обработки.

        :return: Отсутствуют возвращаемые значения.
        """
        loop = asyncio.get_running_loop()

        with ThreadPoolExecutor(max_workers=1) as threadpool:
            while True:
                nn_input, future_result = await self.image_queue.get()

                try:
                    async with self.device_lock:
                        result = await loop.run_in_executor(
                            threadpool,
                            self.predictor.batch_predict,
                            *nn_input
                        )
                    future_result.set_result(result)

                except InvalidStateError:
                    # Уже установлен результат для футуры
                    continue

    async def add_players_inference_task_to_queue(self, *images: numpy.ndarray) -> Future[list[Instances]]:
        """
        Добавляет задачу получения разметки поля.

        :param images: Изображения в формате BGR из OpenCV для обработки.
        :return: Футура с ожиданием обработки изображения.
        """
        future_result: Future[list[Instances]] = Future()
        # Добавить задачу генерации разметки поля
        await self.image_queue.put((images, future_result))

        return future_result