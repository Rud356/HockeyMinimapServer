from pathlib import Path
from typing import Annotated, Optional

import cv2
from dishka import FromDishka
from fastapi import APIRouter, HTTPException, Query

from server.algorithms.data_types import Mask
from server.algorithms.services.field_predictor_service import FieldPredictorService
from server.algorithms.video_processing import VideoProcessing
from server.controllers.dto.inference_anchor_point import InferenceAnchorPoint
from server.controllers.dto.points_mapping import PointsMapping
from server.controllers.endpoints_base import APIEndpoint
from server.controllers.exceptions import UnauthorizedResourceAccess
from server.data_storage.dto import MinimapDataDTO, UserDTO, VideoDTO
from server.data_storage.dto.relative_point_dto import RelativePointDTO
from server.data_storage.exceptions import DataIntegrityError, NotFoundError
from server.data_storage.protocols import Repository
from server.utils.config import AppConfig
from server.utils.file_lock import FileLock
from server.views.map_view import MapView
from server.views.video_view import VideoView


class VideoToMapEndpoint(APIEndpoint):
    def __init__(self, router: APIRouter):
        super().__init__(router)
        self.router.add_api_route(
            "/video/{video_id}/map_points/",
            self.create_point_mapping_for_video,
            methods=["post"],
            description="Создает соотнесения точек из видео с точками мини-карты, "
                        "возвращая число добавленных точек",
            tags=["map"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                    },
                404: {"description": "Видео не найдено"},
            }
        )
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
        self.router.add_api_route(
            "/video/{video_id}/map_points/",
            self.drop_all_mapped_points_for_video,
            methods=["delete"],
            description="Удаляет все соотнесения точек, привязанные к видео, "
                        "и возвращает количество удаленных записей",
            tags=["map"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                    }
            }
        )
        self.router.add_api_route(
            "/video/{video_id}/map_points/inference",
            self.infer_key_points_from_video,
            methods=["get"],
            description="Получает ключевые точки с помощью нейронной сети на основе кадра, "
                        "и опциональной якорной точки, передаваемой в теле запроса",
            tags=["map"],
            responses={
                401: {
                    "description":
                        "Нет валидного токена авторизации или отсутствуют права управление проектами"
                },
                404: {"description": "Видео не найдено"},
                409: {"description": "К видео не была применена коррекция"}
            }
        )
        self.router.add_api_route(
            "/map_points/{map_data_id}",
            self.edit_mapped_point,
            methods=["patch"],
            description="Изменяет точку с конкретным идентификатором",
            tags=["map"],
            responses={
                400: {"description": "Невалидные данные для обновления точки"},
                401: {"description": "Нет валидного токена авторизации или нет прав управления проектами"},
                404: {"description": "Точка не найдена"}
            }
        )

    async def create_point_mapping_for_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int,
        points_mapping: list[PointsMapping]
    ) -> int:
        """
        Создает соотношения точек из видео к точкам на мини-карте.

        :param repository: Объект взаимодействия с БД.
        :param current_user: Пользователь системы.
        :param video_id: Идентификатор видео.
        :param points_mapping: Соотношения точек на карте к точкам на камере.
        :return: Количество добавленных точек.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await MapView(repository).create_point_mapping_for_video(
                video_id,
                {mapped.map_point: mapped.video_point for mapped in points_mapping}
            )

        except DataIntegrityError as err:
            raise HTTPException(
                404, "Video doesn't exists, or point not found"
            ) from err

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

    async def drop_all_mapped_points_for_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        video_id: int
    ) -> int:
        """
        Удаляет все соотнесенные точки из БД, привязанные к видео.

        :param repository: Объект доступа к БД.
        :param current_user: Текущий пользователь системы.
        :param video_id: Идентификатор видео.
        :return: Сколько записей было удалено.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        deleted: int = await MapView(repository).drop_all_mapping_points_for_video(video_id)

        return deleted

    async def edit_mapped_point(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        map_data_id: int,
        point_on_camera: Optional[RelativePointDTO] = None,
        point_on_minimap: Optional[RelativePointDTO] = None,
        is_used: Optional[bool] = None
    ) -> bool:
        """
        Изменяет конкретную точку с данными.

        :param repository: Объект доступа к БД.
        :param current_user: Текущий пользователь системы.
        :param map_data_id: Идентификатор точки.
        :param point_on_camera: Новое значение положения на камере.
        :param point_on_minimap: Новое значение положения на мини-карте.
        :param is_used: Нужно ли использовать эту точку.
        :return: Была ли изменена точка.
        """
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to modify project"
            )

        try:
            return await MapView(repository).edit_point_from_mapping(
                map_data_id,
                point_on_camera,
                point_on_minimap,
                is_used
            )

        except NotFoundError:
            raise HTTPException(
                404,
                "Point was not found"
            )

        except DataIntegrityError:
            raise HTTPException(
                400,
                "Bad point data for update provided"
            )

    async def infer_key_points_from_video(
        self,
        repository: FromDishka[Repository],
        current_user: FromDishka[UserDTO],
        app_config: FromDishka[AppConfig],
        field_predictor: FromDishka[FieldPredictorService],
        file_lock: FromDishka[FileLock],
        video_id: int,
        body: InferenceAnchorPoint,
        frame_timestamp: Annotated[Optional[float], Query(ge=0)] = 0.0
    ) -> list[PointsMapping]:
        if not current_user.user_permissions.can_create_projects:
            raise UnauthorizedResourceAccess(
                "User is required to have permission to create projects to get key points "
                "on frame"
            )

        try:
            video: VideoDTO = await VideoView(repository).get_video(video_id)

        except NotFoundError:
            raise HTTPException(404, "Video with provided ID not found")

        if video.converted_video_path is None:
            raise HTTPException(
                409, "Video did not have a correction applied to it"
            )

        map_view: MapView = MapView(repository)
        video_path: Path = app_config.static_path / "videos" / video.converted_video_path
        field_mask_path: Path = video_path.parent / "field_mask.jpeg"
        video_processing: VideoProcessing = VideoProcessing(app_config.video_processing)

        key_points: dict[RelativePointDTO, RelativePointDTO]
        field_mask: Mask

        key_points, field_mask, *_ = await map_view.get_key_points_from_video(
            video_path,
            video.camera_position,
            app_config.minimap_config,
            video_processing,
            field_predictor,
            frame_timestamp,
            body.anchor_point
        )

        async with file_lock.lock_file(field_mask_path):
            cv2.imwrite(str(field_mask_path.resolve()), field_mask.mask)

        return [
            PointsMapping(map_point=map_point, video_point=video_point)
                for map_point, video_point in key_points.items()
        ]
