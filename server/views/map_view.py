from typing import Optional

from server.algorithms.data_types import CV_Image
from server.algorithms.data_types.field_extracted_data import FieldExtractedData
from server.algorithms.key_point_placer import KeyPointPlacer
from server.algorithms.services.base.field_data_extraction_protocol import FieldDataExtractionProtocol
from server.data_storage.dto import MinimapDataDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.exceptions import NotFoundError
from server.data_storage.protocols import Repository


class UserView:
    """
    Предоставляет интерфейс получения данных о мини-карте и управления ими.
    """
    def __init__(
        self,
        repository: Repository
    ):
        self.repository: Repository = repository

    async def create_point_mapping_for_video(
        self, video_id: int, mapping: dict[RelativePointDTO, RelativePointDTO]
    ) -> int:
        """
        Добавляет соотношения точек карты и игрового поля.

        :param video_id: Идентификатор видео.
        :param mapping: Соотношения точек.
        :return: Количество добавленных точек.
        :raise DataIntegrityError: Нарушена целостность данных, возможно видео не существует.
        """
        async with self.repository.transaction as tr:
            count: int = await self.repository.map_data_repo.create_point_mapping_for_video(
                video_id, mapping
            )
            await tr.commit()

        return count

    async def get_points_mapping_for_video(self, video_id: int) -> list[MinimapDataDTO]:
        """
        Получает все точки соотнесения для видео.

        :param video_id: Идентификатор видео.
        :return: Список точек соотнесения с видео.
        """
        async with self.repository.transaction:
            return await self.repository.map_data_repo.get_points_mapping_for_video(video_id)

    async def drop_all_mapping_points_for_video(self, video_id: int) -> int:
        """
        Удаляет все соотнесенные точки, относящиеся к видео.

        :param video_id: Идентификатор видео.
        :return: Количество удаленных точек.
        :raise NotFoundError: Точки не найдены.
        """
        async with self.repository.transaction as tr:
            count: int = await self.repository.map_data_repo.drop_all_mapping_points_for_video(
                video_id
            )
            await tr.commit()

        if count == 0:
            raise NotFoundError("Points not found for specified video")

        return count

    async def edit_point_from_mapping(
        self,
        map_data_id: int,
        point_on_camera: Optional[RelativePointDTO] = None,
        point_on_minimap: Optional[RelativePointDTO] = None,
        is_used: Optional[bool] = None
    ) -> bool:
        """
        Изменяет конкретное соотношение точек карты с точкой из видео.

        :param map_data_id: Идентификатор соотнесения точек к карте.
        :param point_on_camera: Данные точки на камере.
        :param point_on_minimap: Данные точки на мини-карте.
        :param is_used: Используется ли точка.
        :return: Были ли изменения сохранены.
        :raise NotFoundError: Точка не найдена.
        :raise DataIntegrityError: Переданные данные не верные.
        """
        async with self.repository.transaction as tr:
            modified: bool = await self.repository.map_data_repo.edit_point_from_mapping(
                map_data_id,
                point_on_camera,
                point_on_minimap,
                is_used
            )
            await tr.commit()

        return modified

    async def compute_key_points_of_field_from_frame(
        self,
        frame: CV_Image,
        key_point_placer: KeyPointPlacer,
        field_data_extractor: FieldDataExtractionProtocol,
        anchor_point: Optional[RelativePointDTO]
    ) -> FieldExtractedData:
        ...
