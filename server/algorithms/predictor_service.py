import asyncio
from abc import ABC
from asyncio import Future
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable

import numpy
from detectron2.structures import Instances

from server.algorithms.batch_predictor import BatchPredictor


class PredictorService(ABC):
    """
    Базовый класс для сервисов обработки изображения нейронной сетью.
    """

    predictor: BatchPredictor
    device_lock: asyncio.Lock
    image_queue: asyncio.Queue[
        tuple[
            tuple[numpy.ndarray, ...],
            Future[list[Instances]]
        ]
    ]

    async def __call__(self) -> None:
        """
        Обрабатывает изображения в режиме сервиса на устройстве обработки.

        :return: Отсутствуют возвращаемые значения.
        """
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        with ThreadPoolExecutor(max_workers=1) as threadpool:
            while True:
                nn_inputs, future_result = await self.image_queue.get()
                result: list[Instances] = await self.execute_model(nn_inputs, loop, threadpool)
                future_result.set_result(result)

    async def execute_model(
        self,
        nn_inputs: Iterable[numpy.ndarray],
        loop: asyncio.AbstractEventLoop,
        threadpool: ThreadPoolExecutor
    ) -> list[Instances]:
        """
        Запускает модель нейронной сети на выполнение в отдельном потоке для неблокирующего выполнения.

        :param nn_inputs: Изображение для обработки нейросетью.
        :param loop: Текущий асинхронный цикл.
        :param threadpool: Текущий пул потоков для запуска нейронной сети.
        :return: Список полученных результатов для изображений.
        """
        async with self.device_lock:
            result: list[dict[str, Instances]] = await loop.run_in_executor(
                threadpool,
                self.predictor.batch_predict,
                *nn_inputs
            )
            return [result_instance["instances"] for result_instance in result]

    async def add_inference_task_to_queue(self, *images: numpy.ndarray) -> Future[list[Instances]]:
        """
        Добавляет задачу запуска нейросети на получение данных из изображения.

        :param images: Изображения в формате BGR из OpenCV для обработки.
        :return: Футура с ожиданием результата обработки изображения.
        """
        future_result: Future[list[Instances]] = Future()
        # Добавить задачу генерации разметки поля
        await self.image_queue.put((images, future_result))

        return future_result
