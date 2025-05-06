from typing import Optional, Protocol, runtime_checkable

from server.data_storage.dto.minimap_data_dto import MinimapDataDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.protocols.transaction_manager import TransactionManager


@runtime_checkable
class MapDataRepo(Protocol):
    """
    Управляет данными о мини-карте.
    """
    transaction: TransactionManager

    async def create_point_mapping_for_video(
        self, video_id: int, mapping: dict[RelativePointDTO, RelativePointDTO]
    ) -> int:
        """
        Создает соотнесения точек для видео.

        :param video_id: Идентификатор видео.
        :param mapping: Соотнесение точек с мини-карты к точкам на видео.
        :return: Сколько точек соотнесено.
        :raise DataIntegrityError: Неверные входные данные.
        """

    async def get_points_mapping_for_video(self, video_id: int) -> list[MinimapDataDTO]:
        """
        Получает все точки соотнесения для видео.

        :param video_id: Идентификатор видео.
        :return: Список точек соотнесения с видео.
        """

    async def drop_all_mapping_points_for_video(self, video_id: int) -> int:
        """
        Удаляет все соотнесенные точки, относящиеся к видео.

        :param video_id: Идентификатор видео.
        :return: Количество удаленных записей.
        """

    async def edit_point_from_mapping(
        self,
        map_data_id: int,
        point_on_camera: Optional[RelativePointDTO] = None,
        point_on_minimap: Optional[RelativePointDTO] = None,
        is_used: Optional[bool] = None
    ) -> bool:
        """
        Изменяет информацию о точках соотнесения.

        :param map_data_id: Идентификатор соотнесения.
        :param point_on_camera: Точка из камеры (при значении None - не изменяется).
        :param point_on_minimap: Точка из мини-карты (при значении None - не изменяется).
        :param is_used: Используется ли точка в построении карты (при значении None - не изменяется).
        :return: Изменена ли точка.
        :raises NotFoundError: Точка не найдена.
        :raises DataIntegrityError: Если наружены ограничения целостности.
        """
