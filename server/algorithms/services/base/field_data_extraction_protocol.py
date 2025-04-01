from typing import Optional, Protocol, TYPE_CHECKING, runtime_checkable

from detectron2.structures import Instances

from server.algorithms.data_types.field_extracted_data import FieldExtractedData

if TYPE_CHECKING:
    from server.algorithms.data_types import Point


@runtime_checkable
class FieldDataExtractionProtocol(Protocol):
    """
    Определяет интерфейс для сервиса получения данных о выделениях ключевых точек на поле.
    """

    def get_field_data(
        self,
        detectron2_output: Instances,
        anchor_center_point: Optional[Point] = None
    ) -> FieldExtractedData:
        """
        Преобразует вывод Detectron2 в соотнесение точек с точками мини-карты.

        :param detectron2_output: Вывод нейросети.
        :param anchor_center_point: Пользовательская ключевая точка.
        :return: Информация о соотнесении точек и маске игрового поля на видео.
        """
