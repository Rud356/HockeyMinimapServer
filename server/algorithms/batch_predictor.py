import numpy
import torch
from detectron2.engine import DefaultPredictor
from detectron2.structures import Instances

from server.algorithms.data_types.detectron2_input import Detectron2Input


class BatchPredictor(DefaultPredictor):
    def batch_predict(self, *images: numpy.ndarray) -> list[Instances]:
        """
        Используется для получения выделений сразу на нескольких изображениях в BRG формате
        (формат по умолчанию OpenCV).

        :return: Список из полученных выделений на изображении
            в порядке передачи изображений.
        """

        with torch.no_grad():
            # Преобразование изображений в BGR
            if self.input_format == "RGB":
                images = [image[:, :, ::-1] for image in images]

            # Подготовка входных данных
            dimensions: list[tuple[int, ...]] = [image.shape[:2] for image in images]
            image_tensors: list[torch.Tensor] = [
                torch.as_tensor(
                    image.astype("float32").transpose(2, 0, 1)
                ) for image in images
            ]

            # Входной формат для нейросети
            inputs: list[Detectron2Input] = []

            for image_dimension, image in zip(dimensions, image_tensors):
                image.to(self.cfg.MODEL.DEVICE)
                height, width = image_dimension
                input_value: Detectron2Input = Detectron2Input(
                    image=image, height=height, width=width
                )
                inputs.append(input_value)

            # Выполнение обработки нейросетью
            results: list[Instances] = self.model(inputs)
            return results
