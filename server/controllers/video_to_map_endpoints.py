from dishka import FromDishka
from fastapi import APIRouter

from server.controllers.endpoints_base import APIEndpoint
from server.data_storage.dto import MinimapDataDTO, UserDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.protocols import Repository


class VideoUploadEndpoint(APIEndpoint):
    def __init__(self, router: APIRouter):
        super().__init__(router)

    async def get_points_mapped_to_minimap(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int
    ) -> list[MinimapDataDTO]:
        """
        Получает информацию о соотнесенных точках видео с точками карты для конкретного видео.

        :param repository: Объект доступа к БД.
        :param current_user: Текущий пользователь системы.
        :param video_id: Идентификатор видео.
        :return: Объект соотнесений точек.
        """
