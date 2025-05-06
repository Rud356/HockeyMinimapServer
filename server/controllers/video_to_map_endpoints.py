from dishka import FromDishka
from fastapi import APIRouter

from server.controllers.endpoints_base import APIEndpoint
from server.data_storage.dto import MinimapDataDTO, UserDTO
from server.data_storage.protocols import Repository
from server.views.map_view import MapView


class VideoToMapEndpoint(APIEndpoint):
    def __init__(self, router: APIRouter):
        super().__init__(router)
        self.router.add_api_route(
            "/video/{video_id}/map_points/",
            self.get_points_mapped_to_minimap,
            methods=["get"],
            description="Получает все точки соотнесения видео с мини-картой",
            tags=["map"],
            responses={
                401: {"description": "Нет валидного токена авторизации"}
            }
        )
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
        return await MapView(repository).get_points_mapping_for_video(video_id)
